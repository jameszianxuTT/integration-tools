# comment.sh

## Overview

When a metal uplift PR is up, this generates a copyable comment with the list of commits and CI runs.

## Usage

```bash
./show/comment.sh
```

## Examples

```md
Brings [129 metal commits](https://github.com/tenstorrent/tt-metal/compare/1c6f2b7a835ff8a9ca20d024cbf7e8cba4c53a69...1bf766759336490eeeb626f7b4e94bf5ab81eb8f)
<details><summary> Click to expand commits ◀ </summary>

```j
> git log 1c6f2b7a835ff8a9ca20d024cbf7e8cba4c53a69..1bf766759336490eeeb626f7b4e94bf5ab81eb8f --format="%cd %h by %an|||: %s" --date=short-local | column -t -s "|||"
2025-09-08 1bf7667593 by Author_1              : YOLOv7 Performance Optimization (#27765)
2025-09-08 2808d9837f by Author_2  : #0: Set default value for elu (#28072)
...
2025-09-03 74fbc1711c by Author_3                   : Remove unnecessary quotes after introducing shlex.quote (#27833)
2025-09-03 a9ff25412a by Author_4                : Change SFPMUL to SFPMAD in cases where a MAD, not a MUL, is being done (#27811)
```

</details>


FE CI runs:
- [x] tt-torch CI
- [x] tt-forge-fe CI
- [x] tt-xla CI
```