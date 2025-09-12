#!/usr/bin/env python3
import git 
import os
import argparse
import subprocess
from pprint import pprint
REPOS = {
    "tt-torch": "https://github.com/tenstorrent/tt-torch.git",
    "tt-xla": "https://github.com/tenstorrent/tt-xla.git",
    "tt-forge-fe": "https://github.com/tenstorrent/tt-forge-fe.git",
    
    # not FEs
    "tt-mlir": "https://github.com/tenstorrent/tt-mlir.git",
    "tt-metal": "https://github.com/tenstorrent/tt-metal.git",    
}

REPOS_SSH = {
    "tt-torch": "git@github.com:tenstorrent/tt-torch.git",
    "tt-xla": "git@github.com:tenstorrent/tt-xla.git",
    "tt-forge-fe": "git@github.com:tenstorrent/tt-forge-fe.git",
    
    # not FEs
    "tt-mlir": "git@github.com:tenstorrent/tt-mlir.git",
    "tt-metal": "git@github.com:tenstorrent/tt-metal.git",    
}

mlir2fe_uplift_commits = {} # map of frontend commits uplifting tt-mlir to their actual tt-mlir uplift commits
metal2mlir_uplift_commits = {}

def get_mlir_change_from_mlir_uplift_commit(commit, fe_repo_name):
    """
    Extract the before/after tt-mlir commit hashes from a frontend uplift commit.
    For tt-torch/tt-xla: parse third_party/CMakeLists.txt diff.
    For tt-forge-fe: parse submodule change in third_party/tt-mlir.
    Returns (before_hash, after_hash)
    """
    diff = commit.diff(commit.parents[0] if commit.parents else None, create_patch=True)
    before_hash = None
    after_hash = None
    if fe_repo_name in ["tt-torch", "tt-xla"]:
        # Look for CMakeLists.txt diff
        for d in diff:
            if d.a_path and "third_party/CMakeLists.txt" in d.a_path:
                for line in d.diff.decode().splitlines():
                    if line.startswith("-set(TT_MLIR_VERSION ") or line.startswith("-    set(TT_MLIR_VERSION "):
                        before_hash = line.split('"')[1]
                    if line.startswith("+set(TT_MLIR_VERSION ") or line.startswith("+    set(TT_MLIR_VERSION "):
                        after_hash = line.split('"')[1]
    elif fe_repo_name == "tt-forge-fe":
        # Look for submodule change in third_party/tt-mlir
        for d in diff:
            if d.a_path and "third_party/tt-mlir" in d.a_path and d.new_file is False and d.deleted_file is False:
                # Submodule diff: lines like -Subproject commit <hash> and +Subproject commit <hash>
                for line in d.diff.decode().splitlines():
                    if line.startswith("-Subproject commit "):
                        before_hash = line.split()[-1]
                    if line.startswith("+Subproject commit "):
                        after_hash = line.split()[-1]
    return (before_hash, after_hash)

def get_metal_change_from_metal_uplift_commit(commit):
    """
    Extract the before/after tt-metal commit hashes from a tt-metal uplift commit into tt-mlir.
    Handles both CMakeLists.txt (TT_METAL_VERSION) and submodule diffs (third_party/tt-metal).
    Returns (before_hash, after_hash)
    """
    diff = commit.diff(commit.parents[0] if commit.parents else None, create_patch=True)
    before_hash = None
    after_hash = None
    for d in diff:
        if d.a_path and "third_party/CMakeLists.txt" in d.a_path:
            # print("identified metal uplift commit from CMakeLists.txt diff", commit.message)
            # print(d.diff.decode())
            for line in d.diff.decode().splitlines():
                if line.startswith("-set(TT_METAL_VERSION "):
                    before_hash = line.split('"')[1]
                if line.startswith("+set(TT_METAL_VERSION "):
                    after_hash = line.split('"')[1]
    return (before_hash, after_hash)
    

def is_mlir_uplift_commit(commit):
    """
    Check if the commit message indicates a tt-mlir uplift.
    """
    is_mlir_uplift_commit = "Uplift third_party/tt-mlir" in commit.message
    return is_mlir_uplift_commit

def pull_or_clone_repo(repo_name, branch='main'):
    """
    Pull or clone the repository if it doesn't exist.
    """
    if not os.path.exists(repo_name):
        print(f"Cloning {repo_name}...")
        git.Repo.clone_from(REPOS_SSH[repo_name], repo_name)
        repo = git.Repo(repo_name)
        if branch != 'main':
            try:
                repo.git.checkout(branch)
            except git.exc.GitCommandError:
                print(f"Branch '{branch}' doesn't exist in {repo_name}, staying on default branch")
    else:
        repo = git.Repo(repo_name)
        try:
            repo.git.checkout(branch)  # Ensure we are on the specified branch
            print(f"Pulling {repo_name} on branch {branch}...")
            repo.remotes.origin.pull()
        except git.exc.GitCommandError:
            print(f"Branch '{branch}' doesn't exist in {repo_name}, staying on current branch")

def initialize_repos():
    """
    Ensure tt-mlir and tt-metal repos are present and up to date.
    """
    for repo in ["tt-mlir", "tt-metal"]:
        pull_or_clone_repo(repo)

def get_commit_range(repo_name, start_commit, end_commit, branch='main'):
    """
    Get a list of commits in the specified range.
    """
    pull_or_clone_repo(repo_name, branch)
    repo = git.Repo(repo_name)
    commits = list(repo.iter_commits(f"{start_commit}..{end_commit}"))
    return commits

def create_uplift_commit_mappings(fe_commit_range, repo_name, fe_only=False):
    """
    Expand tt-mlir uplift commits into corresponding frontend commits.
    Then recurisvely expand tt-mlir commits into tt-metal commits (unless fe_only is True).
    """
    
    for commit in fe_commit_range:
        _commit:git.Commit = commit
        if is_mlir_uplift_commit(_commit):
            curr,prev = get_mlir_change_from_mlir_uplift_commit(_commit, repo_name)
            if curr and prev:
                # Store the uplifted MLIR commit range
                mlir_commit_range = get_commit_range("tt-mlir", prev + "^", curr)
                mlir2fe_uplift_commits[_commit.hexsha] = mlir_commit_range
                
                # recursively find metal uplift commits from mlir commits (only if not fe_only)
                if not fe_only:
                    for mlir_commit in mlir_commit_range:
                        metal_commit_curr,metal_commit_prev = get_metal_change_from_metal_uplift_commit(mlir_commit)
                        if metal_commit_prev and metal_commit_curr:
                            # Store the uplifted metal commit range
                            metal2mlir_uplift_commits[mlir_commit.hexsha] = get_commit_range("tt-metal", metal_commit_prev + "^", metal_commit_curr)
                
                # print(f"Identified uplifted MLIR commit range: {prev} -> {curr} for commit {_commit.hexsha}")        
    
    # pprint(mlir2fe_uplift_commits)
    # pprint(metal2mlir_uplift_commits)
    # return mlir2fe_uplift_commits


def build_uplift_tree_with_all_fe(fe_commit_range):
    """
    Build a nested tree structure including all FE commits (uplift and non-uplift).
    Returns a dict: {fe_commit_sha: {"commit": commit_obj, "mlir_commits": [...], "mlir": {mlir_commit_sha: {"commit": mlir_commit_obj, "metal_commits": [...]}}}}
    """
    tree = {}
    for fe_commit in fe_commit_range:
        fe_sha = fe_commit.hexsha
        mlir_commits = mlir2fe_uplift_commits.get(fe_sha, [])
        tree[fe_sha] = {"commit": fe_commit, "mlir_commits": [], "mlir": {}}
        for mlir_commit in mlir_commits:
            mlir_sha = mlir_commit.hexsha
            tree[fe_sha]["mlir_commits"].append(mlir_sha)
            metal_commits = metal2mlir_uplift_commits.get(mlir_sha, [])
            tree[fe_sha]["mlir"][mlir_sha] = {
                "commit": mlir_commit,
                "metal_commits": [c.hexsha for c in metal_commits],
                "metal": {c.hexsha: c for c in metal_commits}
            }
    return tree

def print_commit_info(commit, color, indent):
    short_sha = commit.hexsha[:8]
    date = commit.committed_datetime.strftime('%Y-%m-%d')
    author = commit.author.name
    msg = commit.message.split('\n', 1)[0]
    print(f"{indent}{color}{short_sha} | {date} | {author} | {msg}{' ' * (80 - len(msg))}{chr(27)}[0m")

def print_uplift_tree_with_all(tree):
    CYAN = '\033[1;36m'
    YELLOW = '\033[1;33m'
    GREEN = '\033[1;32m'
    RESET = '\033[0m'
    print(f"{CYAN}Uplift Tree:{RESET}")
    for fe_sha, fe_data in tree.items():
        print_commit_info(fe_data["commit"], GREEN, "  ")
        for mlir_sha in fe_data["mlir_commits"]:
            mlir_data = fe_data["mlir"][mlir_sha]
            print_commit_info(mlir_data["commit"], YELLOW, "    ")
            for metal_sha in mlir_data["metal_commits"]:
                metal_commit = mlir_data["metal"].get(metal_sha)
                if metal_commit:
                    print_commit_info(metal_commit, CYAN, "      ")

def flatten_uplift_tree(tree, fe_only=False):
    """
    Returns a linear list of (fe_commit, mlir_commit, metal_commit) tuples in in-order traversal.
    If fe_only is True, metal_commit will always be None (keeps metal uplifts intact).
    """
    linear_history = []
    for fe_sha, fe_data in tree.items():
        fe_commit = fe_data["commit"]
        if not fe_data["mlir_commits"]:
            # Plain FE commit
            linear_history.append((fe_commit, None, None))
        else:
            for mlir_sha in fe_data["mlir_commits"]:
                mlir_data = fe_data["mlir"][mlir_sha]
                mlir_commit = mlir_data["commit"]
                if fe_only or not mlir_data["metal_commits"]:
                    # MLIR uplift, no metal uplift (or fe_only mode)
                    linear_history.append((fe_commit, mlir_commit, None))
                else:
                    for metal_sha in mlir_data["metal_commits"]:
                        metal_commit = mlir_data["metal"][metal_sha]
                        # Metal uplift: flatten to individual metal commits
                        linear_history.append((fe_commit, mlir_commit, metal_commit))
    return linear_history

def update_cmakelists_version(cmakelists_path, var_name, new_hash):
    """
    Update the given variable in CMakeLists.txt to the new hash.
    """
    import re
    with open(cmakelists_path, 'r') as f:
        lines = f.readlines()
    pattern = re.compile(rf'set\({var_name} ".*"\)')
    new_line = f'set({var_name} "{new_hash}")\n'
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = new_line
    with open(cmakelists_path, 'w') as f:
        f.writelines(lines)

def create_flattened_mlir_branch(linear_history, mlir_repo_path, base_branch="main", new_branch="jzx/uplift_tree"):
    repo = git.Repo(mlir_repo_path)
    repo.git.checkout(base_branch)
    # Delete branch if exists
    if new_branch in repo.heads:
        repo.git.branch('-D', new_branch)
    repo.git.checkout('-b', new_branch)
    cmakelists_path = os.path.join(mlir_repo_path, 'third_party', 'CMakeLists.txt')
    mlir_map = {}  # (orig_mlir_hash, orig_metal_hash) -> new_commit.hexsha
    for _, mlir_commit, metal_commit in linear_history:
        if mlir_commit is None:
            continue
        repo.git.checkout(mlir_commit.hexsha, '--', '.')
        # Update TT_METAL_VERSION if this is a metal uplift
        if metal_commit:
            update_cmakelists_version(cmakelists_path, 'TT_METAL_VERSION', metal_commit.hexsha)
        update_cmakelists_version(cmakelists_path, 'TT_MLIR_VERSION', mlir_commit.hexsha)
        repo.git.add(A=True)
        # Compose commit message
        msg = f"orig_fe=None | orig_mlir={mlir_commit.hexsha[:8]} | orig_metal={metal_commit.hexsha[:8] if metal_commit else 'None'}"
        msg_body = f"\n\n[MLIR:{mlir_commit.hexsha[:8]}] {mlir_commit.message.splitlines()[0]}"
        if metal_commit:
            msg_body += f"\n[METAL:{metal_commit.hexsha[:8]}] {metal_commit.message.splitlines()[0]}"
        new_commit = repo.index.commit(msg + msg_body, author=mlir_commit.author, committer=mlir_commit.committer, author_date=mlir_commit.authored_datetime, commit_date=mlir_commit.committed_datetime)
        mlir_map[(mlir_commit.hexsha, metal_commit.hexsha if metal_commit else None)] = new_commit.hexsha
    return mlir_map


def apply_patch_if_needed(repo, fe_commit, mlir_commit, metal_commit, patch_mappings):
    """
    Apply patches if this commit matches any of the specified MLIR commits.
    patch_mappings: dict of {mlir_commit_hash: patch_file_path}
    """
    if not patch_mappings or not mlir_commit:
        return
    
    mlir_hash = mlir_commit.hexsha
    # Also check for partial hash matches (in case user provided short hash)
    matching_patches = []
    for patch_hash, patch_path in patch_mappings.items():
        if mlir_hash.startswith(patch_hash) or patch_hash.startswith(mlir_hash[:8]):
            matching_patches.append(patch_path)
    
    for patch_path in matching_patches:
        print(f"Applying patch {patch_path} for MLIR commit {mlir_hash[:8]}")
        try:
            # Apply the patch
            repo.git.apply(patch_path)
            print(f"Successfully applied patch {patch_path}")
        except git.exc.GitCommandError as e:
            print(f"Warning: Failed to apply patch {patch_path}: {e}")

def create_flattened_fe_branch(linear_history, fe_repo_path, mlir_map, base_branch="main", new_branch="jzx/uplift_tree", patch_mappings=None):
    repo = git.Repo(fe_repo_path)
    repo.git.checkout(base_branch)
    # Delete branch if exists. for clean reset logic
    if new_branch in repo.heads:
        repo.git.branch('-D', new_branch)
    repo.git.checkout('-b', new_branch)
    cmakelists_path = os.path.join(fe_repo_path, 'third_party', 'CMakeLists.txt')
    for fe_commit, mlir_commit, metal_commit in linear_history:
        repo.git.checkout(fe_commit.hexsha, '--', '.')
        # Update TT_MLIR_VERSION to the new MLIR commit hash from the flattened branch
        if mlir_commit:
            new_mlir_hash = mlir_map.get((mlir_commit.hexsha, metal_commit.hexsha if metal_commit else None))
            if new_mlir_hash:
                update_cmakelists_version(cmakelists_path, 'TT_MLIR_VERSION', new_mlir_hash)
        
        # Apply patch if needed for this MLIR commit
        apply_patch_if_needed(repo, fe_commit, mlir_commit, metal_commit, patch_mappings)
        
        repo.git.add(A=True)
        msg = f"orig_fe={fe_commit.hexsha[:8]} | orig_mlir={mlir_commit.hexsha[:8] if mlir_commit else 'None'} | orig_metal={metal_commit.hexsha[:8] if metal_commit else 'None'}"
        msg_body = f"\n\n[FE:{fe_commit.hexsha[:8]}] {fe_commit.message.splitlines()[0]}"
        if mlir_commit:
            msg_body += f"\n[MLIR:{mlir_commit.hexsha[:8]}] {mlir_commit.message.splitlines()[0]}"
        if metal_commit:
            msg_body += f"\n[METAL:{metal_commit.hexsha[:8]}] {metal_commit.message.splitlines()[0]}"
        repo.index.commit(msg + msg_body, author=fe_commit.author, committer=fe_commit.committer, author_date=fe_commit.authored_datetime, commit_date=fe_commit.committed_datetime)


def print_flattened_uplift_table(fe_repo_path, branch_name="jzx/uplift_tree"):
    """
    Print a table mapping new FE commits in the flattened branch to their original FE, MLIR, and METAL commits and messages.
    The commit message column is prioritized: [METAL] > [MLIR] > [FE].
    Color the row based on which message is present (CYAN for METAL, YELLOW for MLIR, GREEN for FE).
    """
    import re
    repo = git.Repo(fe_repo_path)
    commits = list(repo.iter_commits(branch_name))
    CYAN = '\033[1;36m'
    YELLOW = '\033[1;33m'
    GREEN = '\033[1;32m'
    RESET = '\033[0m'
    print("\nFlattened Uplift Table (new FE branch):\n")
    print(f"{'NEW_FE':10} | {'ORIG_FE':10} | {'ORIG_MLIR':10} | {'ORIG_METAL':10} | MESSAGE")
    print("-" * 120)
    for commit in commits:
        # Parse commit message for orig_fe, orig_mlir, orig_metal
        m = re.search(r"orig_fe=([0-9a-f]+) \| orig_mlir=([0-9a-f]+|None) \| orig_metal=([0-9a-f]+|None)", commit.message)
        if m:
            orig_fe, orig_mlir, orig_metal = m.groups()
        else:
            orig_fe = orig_mlir = orig_metal = "?"
            break
        # Extract [METAL], [MLIR], [FE] messages in order of priority
        msg = ""
        color = RESET
        lines = commit.message.splitlines()
        metal_msg = next((l for l in lines if l.startswith("[METAL:")), None)
        mlir_msg = next((l for l in lines if l.startswith("[MLIR:")), None)
        fe_msg = next((l for l in lines if l.startswith("[FE:")), None)
        if metal_msg:
            msg = metal_msg
            color = CYAN
        elif mlir_msg:
            msg = mlir_msg
            color = YELLOW
        elif fe_msg:
            msg = fe_msg
            color = GREEN
        else:
            msg = next((l for l in lines if l and not l.startswith("orig_fe=")), lines[-1] if lines else "")
            color = RESET
        print(f"{color}{commit.hexsha[:8]:10} | {orig_fe:10} | {orig_mlir:10} | {orig_metal:10} | {msg}{RESET}")

def prompt_and_force_push(fe_repo, mlir_repo, branch="jzx/uplift_tree"):
    """
    Prompt the user to confirm force-pushing both FE and MLIR uplift branches to remote.
    """
    import sys
    prompt = f"\nWARNING: This will force-push local branches '{branch}' to origin for both {fe_repo} and {mlir_repo}. This will overwrite remote branches if they exist.\nProceed? [y/N]: "
    resp = input(prompt)
    if resp.lower() == 'y':
        import subprocess
        print(f"Force pushing {mlir_repo}:{branch} ...")
        subprocess.run(["git", "-C", mlir_repo, "push", "origin", branch, "--force"], check=True)
        print(f"Force pushing {fe_repo}:{branch} ...")
        subprocess.run(["git", "-C", fe_repo, "push", "origin", branch, "--force"], check=True)
        print("Force push complete.")
    else:
        print("Aborted force-push.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frontend", choices=REPOS.keys(), help="Frontend repo name (e.g. tt-xla)")
    parser.add_argument("start_commit", help="Start commit (exclusive, append ^ to include first commit). Can be relative to HEAD, eg HEAD~5")
    parser.add_argument("end_commit", nargs="?", default="HEAD", help="End commit (inclusive). Default to HEAD if not specified")
    parser.add_argument("--fe-only", action="store_true", help="Only unroll MLIR -> FE uplifts, keep metal uplifts intact")
    parser.add_argument("--fe-branch", default="main", help="FE branch to use as base for commit range and new branch creation (default: main)")
    parser.add_argument("--patch", action="append", nargs=2, metavar=("MLIR_COMMIT", "PATCH_FILE"), 
                        help="Apply patch file at specific MLIR commit. Can be used multiple times. Format: --patch <mlir_commit_hash> <patch_file_path>")
    args = parser.parse_args()
    
    # Process patch mappings
    patch_mappings = {}
    if args.patch:
        for mlir_commit, patch_file in args.patch:
            if not os.path.exists(patch_file):
                print(f"Error: Patch file {patch_file} does not exist")
                return 1
            # Convert to absolute path to avoid issues when changing directories
            abs_patch_path = os.path.abspath(patch_file)
            patch_mappings[mlir_commit] = abs_patch_path
            print(f"Will apply patch {abs_patch_path} for MLIR commit {mlir_commit}")
    
    # Print operation summary
    mode = "FE-only" if args.fe_only else "Full"
    print(f"Starting {mode} uplift unrolling for {args.frontend} from {args.start_commit} to {args.end_commit}")
    if patch_mappings:
        print(f"Will apply {len(patch_mappings)} patch(es) at specific MLIR commits:")
        for mlir_hash, patch_file in patch_mappings.items():
            print(f"  - {mlir_hash} -> {patch_file}")
    
    initialize_repos()
    
    commits = get_commit_range(args.frontend, args.start_commit, args.end_commit, args.fe_branch)
    create_uplift_commit_mappings(commits, args.frontend, fe_only=args.fe_only)
    
    # build & print uplift tree for debug/inspection purposes
    tree = build_uplift_tree_with_all_fe(commits)
    # print_uplift_tree_with_all(tree)
    
    linear_history = flatten_uplift_tree(tree, fe_only=args.fe_only)
    linear_history = linear_history[::-1]  # Reverse to chronological order

    # Debug: show MLIR commits that will be processed
    if patch_mappings:
        print("\nMLIR commits found in uplift tree:")
        for fe_commit, mlir_commit, metal_commit in linear_history:
            if mlir_commit:
                print(f"  - {mlir_commit.hexsha[:8]} | {mlir_commit.message.splitlines()[0][:60]}")
        print()

    mlir_map = create_flattened_mlir_branch(linear_history, 'tt-mlir', base_branch='main')
    create_flattened_fe_branch(linear_history, args.frontend, mlir_map, base_branch=args.fe_branch, patch_mappings=patch_mappings)
    

    # Print the flattened uplift table (new FE branch)
    print_flattened_uplift_table(args.frontend)

    # Prompt to force-push branches
    prompt_and_force_push(args.frontend, 'tt-mlir')
    

if __name__ == "__main__":
    main()
    
# test case 
# ./autobisect.py tt-torch 646aee02 601cc121
# ./autobisect.py tt-torch 646aee02 601cc121 --fe-only
# ./autobisect.py tt-torch 646aee02 601cc121 --fe-branch uplift --patch abc123def path/to/fix.patch
# ./autobisect.py tt-torch 646aee02 601cc121 --patch abc123def path/to/fix1.patch --patch def456ghi path/to/fix2.patch


'''
One problem when "unrolling" uplift commits is that they are rarely pure uplifts, and often
include patches targeting other files than the cmakelists.

Those patches might only be applicable after certain sub-commits only, but we can't know 
automatically which sub-commits to squash uplift patches to.

Eg. In tt-metal -> tt-mlir uplift commit.
Uplifting tt-metal commits: A - B - C - D

commit C introduces a tt-mlir build failure due to function sig change in tt-metal.
Uplift commit in tt-mlir includes a patch to fix this, but that patch is only valid AFTER commit C

We can either batch all the patches and apply them at the START: (PATCH - A - B - C - D) which introduces
a build failure for (A, B)

Or apply them at the END (A - B - C - D - PATCH) which introduces a build failure for (C, D)

This situation becomes yet more complicated for multi-patch situations which are frequent, and patches from uplift commits may 
need to be manually applied to the correct commit in the flattened branch, which is nontrivial to do or find out.

One partial solution - provide --fe-only flag to only unroll MLIR -> FE uplifts, and keep metal uplifts intact.
'''