import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from pathlib import Path
import argparse

from backends.vllm_client import VLLMClient  

# Custom Data Mapper
class FlexibleDataMapper:
    def map(self, raw_sample: dict) -> dict:
        return {
            "sample_id": raw_sample.get("idx"),
            "question": raw_sample.get("instruction"),
            "answer": raw_sample.get("output"),
            "truth": raw_sample.get("gt"),
            "need_search": raw_sample.get("need_search", False),  # added
        }

# Custom Prompt Builder
class DartPromptBuilder:
    def __init__(self, prompt_mode: str = "build"):
        # Allowed values: build / explore
        self.prompt_mode = prompt_mode

    def build(self, data: dict) -> str:
        if self.prompt_mode == "build":
            return f"""
                Problem: {data["question"]}
                Existing reasoning path: {data["answer"]}
                Guidelines for continuing the reasoning:
                1. Understand the existing path: Carefully analyze the existing reasoning path and understand the logic and basis of each step.
                2. Identify the next step: Based on the last step of the existing path, determine the possible directions for the next step of reasoning.
                3. Reason step-by-step: Start from the last step of the existing path and proceed with the reasoning step-by-step.
                4. Final conclusion: When the reasoning is complete, put your final answer within \\boxed{{}}.
            """

        if self.prompt_mode == "explore":
            return f"""
                [Problem]
                {data["question"]}
                [Existing reasoning (read-only; cite only key points when anchoring, do NOT restate the whole text)]
                {data["answer"]}
                [Guidelines (strictly follow)]
                1. Role & Boundaries
                    - Continue only from the last step of the existing reasoning; do not restate or rewrite prior content.
                    - If new symbols/variables are needed, first define their meaning and domain in one sentence, then use them.
                2. Anchoring & Continuation
                    - Use one line to anchor the key equation/state of the “last step” (key points only; do not restate the full text).
                    - If you can determine the next step number from previous steps, continue that numbering; if not, do not number—start reasoning directly.
                3. Explore
                    - Following your own reasoning style and anchored to what has been established, carry the reasoning forward from here.
                Final conclusion: When the reasoning is complete, put your final answer within \\boxed{{}}.
            """


class DartParser:
    def parse(self, raw_response: str, data: dict) -> dict:
        import re
        matches = re.findall(r'\\boxed\{(.*?)\}', raw_response)
        final_answer = matches[-1].strip() if matches else ""
        # return {"final_answer": final_answer}
        return {
            "final_answer": final_answer,
            "raw_response": raw_response
        }

class UnanimousVoteLogic:
    def vote(self, results: list, data: dict) -> dict:
        votes = [r["final_answer"] == data["truth"] for r in results]
        correct_responses = [r["raw_response"] for r, v in zip(results, votes) if v]
        correct_ratio = votes.count(True) / len(votes) if votes else 0.0
        return {
            "correct_ratio": correct_ratio,
            "votes":votes,
            "correct_responses":correct_responses
        }

class JudgingPipeline:
    def __init__(self, prompt_builder, data_mapper, response_parser, vote_logic, client):
        self.prompt_builder = prompt_builder
        self.data_mapper = data_mapper
        self.response_parser = response_parser
        self.vote_logic = vote_logic
        self.client = client

    def judge_sample(self, sample: dict, repeat: int) -> dict:
        data = self.data_mapper.map(sample)

        prompt_mode = getattr(self.prompt_builder, "prompt_mode", "build")
        if prompt_mode == "explore" and not data.get("need_search", False):
            need_search = data.get("need_search", False)
            logging.info("need_search : %s skip!", need_search)
            return {
                "skipped": True,
                "skip_reason": "need_search=False",
                "prompt_mode": prompt_mode,
            }
    
        prompt = self.prompt_builder.build(data)
        responses = [self.client.make_request(prompt) for _ in range(repeat)]
        parsed = [self.response_parser.parse(r, data) for r in responses]
        return self.vote_logic.vote(parsed, data)


def load_processed_ids(out_path: Path) -> set[str]:
    """Load processed sample ids (for resuming from breakpoint)"""
    if not out_path.exists():
        return set()
    with out_path.open("r", encoding="utf-8") as fh:
        return {json.loads(line)["idx"] for line in fh if line.strip()}


def process_jsonl_stream(
    input_file_path: str,
    output_file_path: str,
    repeat: int = 10,
    max_workers: int = 4,
    batch_size: int = 200,          # How many samples per batch
    base_url: str = "http://localhost:8000/v1",
    model: str = "qwen3",
    max_tokens: int = 16384,
    temperature: float = 0.1,
    prompt_mode: str = "build"
):
    client = VLLMClient(base_url=base_url, model=model, max_tokens=max_tokens, temperature=temperature)
    pipeline = JudgingPipeline(
        prompt_builder=DartPromptBuilder(prompt_mode),
        data_mapper=FlexibleDataMapper(),
        response_parser=DartParser(),
        vote_logic=UnanimousVoteLogic(),
        client=client
    )

    in_path  = Path(input_file_path)
    out_path = Path(output_file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total_lines = 0
    with in_path.open("r", encoding="utf-8") as fh:
        for _ in fh:
            total_lines += 1

    processed_ids = load_processed_ids(out_path)
    logging.info("Resume: %d samples already judged", len(processed_ids))
    already_done = len(processed_ids)
    todo_total = total_lines - already_done
    logging.info("Total samples: %d, already judged: %d, to do: %d",
                 total_lines, already_done, todo_total)

    # Read line by line in stream, filter out processed ones
    def iter_todo():
        with in_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                if sample.get("idx") not in processed_ids:
                    yield sample

    # Use generator to read, avoid occupying memory at once
    todo_iter = iter_todo()

    with tqdm(total=total_lines,initial=already_done,desc=out_path.stem, unit="sample") as pbar, \
         out_path.open("a", encoding="utf-8") as fh:

        while True:
            # Read a batch
            batch = list(itertools.islice(todo_iter, batch_size))
            if not batch:
                break   # File read finished

            # Process current batch in parallel
            lock = threading.Lock()
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(pipeline.judge_sample, sample, repeat): sample
                    for sample in batch
                }
                for fut in as_completed(futures):
                    sample = futures[fut]
                    try:
                        result = fut.result()
                        info = result
                    except Exception as e:
                        info = {"correct_ratio": "","votes":"","erro":True}
                        print(f"[ERR] idx={sample.get('idx')} {e}")

                    # Assemble output
                    sample["judge_info"] = info
                    with lock:
                        fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
                        fh.flush()
                    pbar.update(1)
    logging.info("%s finished", out_path.name)


if __name__ == "__main__":
    import logging
    import itertools
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--max_workers", type=int, default=4)
    parser.add_argument("--batch_size", type=int, default=200, help="samples per batch")
    parser.add_argument("--base_url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="qwen3")
    parser.add_argument("--max_tokens", type=int, default=16384)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--prompt_mode", choices=["build", "explore"], default="build")
    
    args = parser.parse_args()

    process_jsonl_stream(
        input_file_path=args.input,
        output_file_path=args.output,
        repeat=args.repeat,
        max_workers=args.max_workers,
        batch_size=args.batch_size,
        base_url=args.base_url,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        prompt_mode=args.prompt_mode
    )