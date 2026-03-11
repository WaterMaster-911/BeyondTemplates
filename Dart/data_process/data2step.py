import json
import os
import sys
import re
from tqdm import tqdm

"""
python data2step2.py ../data/limo.jsonl ../data/limo_processed_raw.jsonl
python data2step2.py ../data/long_cot.jsonl ../data/long_cot_processed_raw.jsonl
"""


def extract_boxed_content(text):
    """
    Extract the content of the last \\boxed{} in the text.
    """
    pattern = r'\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1].strip()
    else:
        return ""


def process_limo_data(input_file, output_file):
    """
    Process a jsonl file, split each item's output by \n\n,
    and create multiple items with cumulative splits.
    Args:
        input_file: input file path
        output_file: output file path
    """
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        total_items = 0
        processed_items = 0
        # Count total lines for progress bar
        with open(input_file, 'r', encoding='utf-8') as f_count:
            total_lines = sum(1 for _ in f_count)
        for item_index, line in enumerate(tqdm(fin, total=total_lines, desc="Processing")):
            line = line.strip()
            if not line:
                continue
            total_items += 1
            item = json.loads(line)
            instruction = item.get('instruction', '')
            input_text = item.get('input', '')
            output = item.get('output', '')
            system = item.get('system', '')
            steps = [step.strip() for step in output.split('\n\n') if step.strip()]
            if not steps:
                continue
            gt = extract_boxed_content(output)

            for step_count in range(1, len(steps) + 1):
                cumulative_output = '\n\n'.join(steps[:step_count])
                idx = str(item_index) + "_" + str(step_count)
                new_item = {
                    'idx': idx,
                    'instruction': instruction,
                    'input': input_text,
                    'output': cumulative_output,
                    'system': system,
                    'gt': gt,
                    'num_steps': step_count,
                    'original_index': item_index,
                    'total_steps': len(steps)
                }
                json.dump(new_item, fout, ensure_ascii=False)
                fout.write('\n')
                processed_items += 1

    print(f"Processing completed!")
    print(f"Original data: {total_items} items")
    print(f"Processed data: {processed_items} items")
    print(f"Output file: {output_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python data2step.py <input_file> <output_file>")
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist!")
        return

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_limo_data(input_file, output_file)

    print("\nExample data (first 3 processed items):")
    with open(output_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            item = json.loads(line)
            print(f"\nItem {i+1}:")
            print(f"  Original index: {item['original_index']}")
            print(f"  Step count: {item['num_steps']}/{item['total_steps']}")
            print(f"  Instruction: {item['instruction'][:100]}...")
            print(f"  Output length: {len(item['output'])} characters")
            print(f"  Ground Truth: {item['gt']}")


if __name__ == "__main__":
    main()