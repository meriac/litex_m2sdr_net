# litex_netcli.py Command Line Reference

`litex_netcli.py` is an interactive command line tool for reading and writing
CSR registers on any LiteX FPGA over Etherbone/UDP.

## Help

```
$ ./litex_netcli.py --help
usage: litex_netcli.py [-h] [-t TARGET] [-c CSR] [-e EXEC] [-i] [-s SCRIPT]

LiteX Etherbone/UDP register access

options:
  -h, --help            show this help message and exit
  -t TARGET, --target TARGET
                        FPGA target host[:port] (default: 192.168.1.50:1234)
  -c CSR, --csr CSR     CSR CSV file (default: None)
  -e EXEC, --exec EXEC  Execute semicolon-delimited commands (default: None)
  -i, --interactive     Interactive command mode (default: False)
  -s SCRIPT, --script SCRIPT
                        Script file to execute (default: None)
```

## Command Line Options

| Option                | Default              | Description                                   |
|-----------------------|----------------------|-----------------------------------------------|
| `-t`, `--target`      | `192.168.1.50:1234`  | FPGA target host[:port]                       |
| `-c`, `--csr`         | *(none)*             | Path to CSR CSV file (enables register names) |
| `-e`, `--exec`        | *(none)*             | Execute semicolon-delimited commands          |
| `-i`, `--interactive` | *(off)*              | Start interactive REPL (verbose, ANSI colors) |
| `-s`, `--script`      | *(none)*             | Execute commands from a script file           |

The `-e`, `-s`, and `-i` options can be combined: exec runs first, then the
script, then the interactive REPL starts.

## Interactive Commands

Once inside the interactive REPL (`-i`) or a script file (`-s`), these commands
are available:

```
litex> help
Commands:
  read  <addr>          Read a register (name or hex address)
  write <addr> <value>  Write a register and read back
  regs  [pattern]       Dump registers, optionally filtered by glob pattern
  csr   [file]          Load/show CSR CSV file
  help                  Show this help
  quit                  Exit interactive mode
```

| Command               | Description                                            |
|-----------------------|--------------------------------------------------------|
| `read <addr>`        | Read a register by name or hex address                 |
| `write <addr> <val>` | Write a value, then read back to confirm               |
| `regs [pattern]`     | Dump registers filtered by glob pattern (`*`, `?`)     |
| `csr [file]`         | Load a CSR CSV at runtime (Tab completes file names)   |
| `help`               | Show command help                                      |
| `quit` / `exit`      | Exit the REPL                                          |

Register addresses can be given as hex (`0x4`) or by name (`ctrl_scratch`).
Named registers require a CSR CSV (via `-c`/`--csr` or the `csr` command).

Values can be written as hex (`0xdeadbeef`), decimal (`42`), or dotted-decimal
IP notation (`192.168.1.100`). The dotted-decimal form is accepted for **any**
register write — it is simply converted to a 32-bit integer
(`192.168.1.100` becomes `0xc0a80164`). On read-back, registers whose name
contains `ip_address` automatically display the dotted-decimal form alongside
the hex value.

## Interactive Features

The interactive REPL (`-i`) provides:

- **Line editing** — arrow keys, Home/End, Ctrl-A/E and other standard readline
  shortcuts
- **History** — Ctrl-R reverse search, Up/Down to recall previous commands;
  history is persisted across sessions in `~/.litex_netcli_history`
- **Tab completion** — press Tab to complete command names, register names,
  and file paths (for the `csr` command)
- **Syntax highlighting** — ANSI color output (auto-disabled when piping to a
  file or non-TTY)

## Examples

All examples below assume the FPGA is reachable at the default IP `192.168.1.50`
on port `1234`.

### Override FPGA target

By default the tool connects to `192.168.1.50` on UDP port `1234`. Use
`-t`/`--target` to target a different FPGA or a non-standard Etherbone port:

```bash
./litex_netcli.py -t 10.0.0.1:5678 -i
```

### Read a register by hex address

```
litex> read 0x4
[0x00000004] = 0x12345678
```

### Read a register by name (requires CSR)

```
litex> read ctrl_scratch
ctrl_scratch @ 0x00000004 = 0x12345678
```

### Write and read-back a register

```
litex> write ctrl_scratch 0xdeadbeef
ctrl_scratch @ 0x00000004 <= 0xdeadbeef
ctrl_scratch @ 0x00000004 = 0xdeadbeef
```

### Write an IP address

```
litex> write eth_rx_streamer_ip_address 192.168.1.100
eth_rx_streamer_ip_address @ 0x00007804 <= 0xc0a80164
eth_rx_streamer_ip_address @ 0x00007804 = 0xc0a80164 (192.168.1.100)
```

### Filter registers by glob pattern

```
litex> regs xadc_*
[0x00002000] = 0x000009ee	# xadc_temperature
[0x00002004] = 0x00000557	# xadc_vccint
[0x00002008] = 0x00000989	# xadc_vccaux
[0x0000200c] = 0x00000558	# xadc_vccbram
[0x00002010] = 0x00000001	# xadc_eoc
[0x00002014] = 0x00000001	# xadc_eos
```

```
litex> regs eth_*_ip_address
[0x00007804] = 0xc0a80164	# eth_rx_streamer_ip_address
[0x00007814] = 0xc0a80164	# eth_tx_streamer_ip_address
```

### Load a CSR file at runtime

Press Tab after `csr` to complete file and directory names.

```
litex> csr
No CSR loaded. Usage: csr <file>
litex> csr csr.csv
Loaded 93 registers from csr.csv
litex> read ctrl_scratch
ctrl_scratch @ 0x00000004 = 0x12345678
```

### Error handling

Using a register name without a CSR file loaded:

```
litex> read ctrl_scratch
Error: Register name 'ctrl_scratch' requires csr
```

Using an invalid register name:

```
litex> read nonexistent_reg
Error: Register 'nonexistent_reg' not found in csr.csv
Available: ctrl_reset, ctrl_scratch, ctrl_bus_errors, ...
```

## Script Files

Script files contain the same commands as the interactive REPL, one per line.
Lines starting with `#` are comments. Example script (`example.m2sdr`):

```bash
# Read and modify the scratch register
read ctrl_scratch
write ctrl_scratch 0xcafebabe
read ctrl_scratch

# Restore original value
write ctrl_scratch 0x12345678
```

Run it:

```
$ ./litex_netcli.py -c csr.csv -s example.m2sdr
ctrl_scratch @ 0x00000004 = 0x12345678
ctrl_scratch @ 0x00000004 <= 0xcafebabe
ctrl_scratch @ 0x00000004 = 0xcafebabe
ctrl_scratch @ 0x00000004 = 0xcafebabe
ctrl_scratch @ 0x00000004 <= 0x12345678
ctrl_scratch @ 0x00000004 = 0x12345678
```

You can combine `-s` and `-i` to run a script then drop into the REPL:

```bash
./litex_netcli.py -c csr.csv -s setup.m2sdr -i
```

### Inline execution with `-e`

The `-e`/`--exec` flag runs semicolon-delimited commands and outputs bare values
(no ANSI, no decoration), making it ideal for shell scripting:

```bash
$ echo "FPGA serial number:" $(./litex_netcli.py -c csr.csv -e "read dna_id")
FPGA serial number: 0x68cc0c7af9e85c
```

```bash
$ ./litex_netcli.py -c csr.csv -e "read ctrl_scratch; read ctrl_bus_errors"
0x12345678
0x00000000
```

```bash
$ ./litex_netcli.py -c csr.csv -e "regs eth_*"
eth_phy_reset 0x00000000
eth_rx_streamer_enable 0x00000001
eth_rx_streamer_ip_address 0x00000000
eth_rx_streamer_udp_port 0x00000929
eth_tx_streamer_enable 0x00000001
eth_tx_streamer_ip_address 0x00000000
eth_tx_streamer_udp_port 0x00000929
```

```bash
# Use in shell variables (quote to preserve newlines)
$ SCRATCH=$(./litex_netcli.py -c csr.csv -e "read ctrl_scratch")
$ echo "Scratch register is $SCRATCH"
Scratch register is 0x12345678
```

### Interactive vs non-interactive output

Without `-i`, output is bare values for easy parsing. With `-i`, output includes
addresses, ANSI colors, and register names. Both support glob patterns:

```bash
$ ./litex_netcli.py -c csr.csv -e "regs eth_*_address"
eth_rx_streamer_ip_address 0x00000000
eth_tx_streamer_ip_address 0x00000000
```

```bash
$ ./litex_netcli.py -c csr.csv -i -e "regs eth_*_address"
[0x00007804] = 0x00000000	# eth_rx_streamer_ip_address
[0x00008004] = 0x00000000	# eth_tx_streamer_ip_address
```
