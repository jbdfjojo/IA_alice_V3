import os

def print_structure(root_dir, level=0, max_level=2, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__'}
    if level > max_level:
        return
    prefix = '    ' * level
    try:
        entries = os.listdir(root_dir)
    except PermissionError:
        return
    for entry in sorted(entries):
        if entry in ignore_dirs:
            continue
        path = os.path.join(root_dir, entry)
        if os.path.isdir(path):
            print(f"{prefix}{entry}/")
            print_structure(path, level + 1, max_level, ignore_dirs)
        else:
            print(f"{prefix}{entry}")

if __name__ == "__main__":
    print_structure('.', max_level=2)
