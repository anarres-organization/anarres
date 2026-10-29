# veri-safe-cyber-bench
veri-safe-cyber-bench

## Smoke outputs

The repo hygiene check rejects `*.out`, so expected smoke outputs are committed as
`tasks/*/public/smoke/NAME.expected`. Run `tools/restore_smoke_out.sh` to write the
`NAME.out` files that `INSTRUCTION.md` describes before packaging a task.
