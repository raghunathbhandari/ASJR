"""Add immediate Discord delivery to the existing external Chakra caller.

Run once on the VPS, then restart the bot using the normal Discord command.
This script never starts or restarts the bot.
"""
import argparse
import ast
from pathlib import Path


def patch_source(source):
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)
             and isinstance(node.func.value, ast.Name)
             and node.func.value.id == 'tp'
             and node.func.attr == 'run_asjr_manual_pipeline']
    if len(calls) != 1:
        raise ValueError('Expected exactly one tp.run_asjr_manual_pipeline call; file unchanged')
    call = calls[0]
    if any(kw.arg == 'alert_sender' for kw in call.keywords):
        return source
    if not any(isinstance(node, ast.Name) and node.id == 'SN' for node in ast.walk(tree)):
        raise ValueError('Expected existing SN notification module; file unchanged')
    # AST columns are UTF-8 byte offsets; retain the caller formatting exactly.
    rows = source.encode('utf-8').splitlines(keepends=True)
    offset = sum(map(len, rows[:call.end_lineno - 1])) + call.end_col_offset - 1
    raw = source.encode('utf-8')
    if raw[offset:offset + 1] != b')':
        raise ValueError('Could not identify pipeline closing parenthesis')
    before = raw[:offset].rstrip()
    separator = b'' if before.endswith((b'(', b',')) else b','
    changed = (before + separator + b' alert_sender=SN.send_to_discord' + raw[offset:]).decode('utf-8')
    ast.parse(changed)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caller', type=Path,
                        default=Path('/root/trading/utils/trading_sudarsan_chakra.py'))
    args = parser.parse_args()
    source = args.caller.read_text(encoding='utf-8')
    changed = patch_source(source)
    if changed == source:
        print('Immediate wick sender already configured; no changes')
        return
    backup = args.caller.with_name(args.caller.name + '.before_immediate_wicks')
    if backup.exists():
        raise FileExistsError(f'Backup already exists: {backup}; caller unchanged')
    backup.write_text(source, encoding='utf-8')
    args.caller.write_text(changed, encoding='utf-8')
    print(f'Immediate wick sender enabled: {args.caller}')
    print(f'Backup: {backup}')
    print('Restart the bot using your normal Discord command; no restart performed here')


if __name__ == '__main__':
    main()
