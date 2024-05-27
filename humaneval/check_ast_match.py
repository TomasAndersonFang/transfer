import json
import javalang
import subprocess
import shutil
import sys
import os
import time
import subprocess
import tempfile
import copy
import hashlib
import re
import argparse

from unidiff import PatchSet
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def run_ast_diff(file1, file2):
    # Define the Java command to execute
    jar_path = "/home/senf/workshop/input-output-repr/eval_result/gumtree-spoon-ast-diff/target/gumtree-spoon-ast-diff-SNAPSHOT-jar-with-dependencies.jar"
    java_class = "/home/senf/workshop/input-output-repr/eval_result/my_project/DiffFiles.java"
    
    cmd = [
        "java", 
        "-cp", 
        f".:{jar_path}", 
        java_class, 
        file1, 
        file2
    ]

    # Execute the command and capture the output
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    return 'no AST change' in result.stdout


def write_patch_to_buggy_file(buggy_file_path, buggy_code, patch):

    with open(buggy_file_path, "r", encoding="ISO-8859-1") as f:
        buggy_class_code = f.read()

    # assert buggy_code in buggy_class_code, "buggy code not in buggy class code"
    fixed_class_code = buggy_class_code.replace(buggy_code, patch)

    
    with open(buggy_file_path, "w", encoding="ISO-8859-1", errors='replace') as f:
        f.write(fixed_class_code)


def main():

    # Parse arguments
    parser = argparse.ArgumentParser("Build dataset with different input-output representations for automated program repair")
    parser.add_argument("--meta_data_path", '-md', type=str, required=True, help="Path to the meta data.")
    parser.add_argument("--buggy_code_file", "-bcf", type=str, action='store', required=True, help="Path to the buggy code file")
    parser.add_argument("--output_path", '-o', type=str, required=True, help="Path to the output.")
    parser.add_argument("--benchmark_path", '-b', type=str, help="Path to the defects4j framework.")

    args = parser.parse_args()

    with open(args.meta_data_path, 'r') as f:
        results = [json.loads(line) for line in f.readlines()]

    with open(args.buggy_code_file, "r") as f:
        buggy_codes = json.load(f)

    cnt_list = [1 if "Plausible" in each['test_results'] else 0 for each in results]
    print("This input-output representation can help model generate plusible patches for {} HumanEval-Java bugs".format(sum(cnt_list)))

    cnt = 0
    for sample in tqdm(results):

        if "Plausible" not in sample['test_results']:
            continue
        
        buggy_file_path = args.benchmark_path + "/src/main/java/humaneval/buggy/{}.java".format(sample['bug_id'])
        fixed_file_path = args.benchmark_path + "/src/main/java/humaneval/correct/{}.java".format(sample['bug_id'])
        buggy_code = buggy_codes[sample['bug_id']]

        patches = sample['patches']

        with open(buggy_file_path, "r") as f:
            buggy_class_code = f.read()

        for i in range(len(patches)):
            if sample['test_results'][i] == "Plausible":

                # shutil.copyfile(buggy_file_path, buggy_file_path + ".bak")
                # time.sleep(1)
                write_patch_to_buggy_file(buggy_file_path, buggy_code, patches[i])
                time.sleep(1)

                match_flag = run_ast_diff(buggy_file_path, fixed_file_path)

                # Recover buggy file
                with open(buggy_file_path, "w") as f:
                    f.writelines(buggy_class_code)

                if match_flag:
                    print("Match!!!")
                    sample['test_results'][i] = "Match"

                # delete modified buggy file
                # os.remove(buggy_file_path)
                # time.sleep(1)
                # restore backup file
                # os.rename(buggy_file_path + ".bak", buggy_file_path)
                # time.sleep(1)
        
        if "Match" in sample["test_results"]:
            cnt += 1

    print("This input-output representation can help model generate exactly matched patches for {} bugs among 162 bugs".format(cnt))


    # Sava results
    with open(args.output_path, 'w') as f:
        for each in results:
            f.write(json.dumps(each) + '\n')


if __name__ == "__main__":
    main()