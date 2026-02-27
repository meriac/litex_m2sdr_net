#!/usr/bin/env python3

# LiteX Etherbone/UDP network CLI.
#
# Interactive command line tool for reading and writing CSR registers on any LiteX FPGA over Etherbone/UDP.
#
# Copyright (c) 2026 Milosch Meriac <milosch@meriac.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import shlex
import atexit
import argparse
import fnmatch
import readline
from litex.tools.remote.comm_udp import CommUDP

# Persistent command history
HISTORY_FILE = os.path.expanduser("~/.litex_netcli_history")
HISTORY_LENGTH = 1000

# ANSI color codes (disabled when not a TTY)
if sys.stdout.isatty():
    C_RESET  = "\033[0m"
    C_BOLD   = "\033[1m"
    C_DIM    = "\033[2m"
    C_RED    = "\033[31m"
    C_GREEN  = "\033[32m"
    C_YELLOW = "\033[33m"
    C_CYAN   = "\033[36m"
else:
    C_RESET = C_BOLD = C_DIM = C_RED = C_GREEN = C_YELLOW = C_CYAN = ""


class litex_netcli:
    """Etherbone/UDP register access for LiteX FPGAs."""

    COMMANDS = {
        "read":  "cmd_read",
        "write": "cmd_write",
        "regs":  "cmd_regs",
        "csr":   "cmd_csr",
    }

    def __init__(self, comm, server, port, csr=None, verbose=False):
        self.comm = comm
        self.server = server
        self.port = port
        self.csr = csr
        self.verbose = verbose

    def close(self):
        self.comm.close()

    def resolve_addr(self, addr_str):
        """Resolve a register name or hex address string to (addr, name, reg|None)."""
        try:
            return int(addr_str, 0), None, None
        except ValueError:
            pass
        if not self.csr:
            print(f"{C_RED}Error:{C_RESET} Register name '{C_BOLD}{addr_str}{C_RESET}' requires csr")
            return None, None, None
        if not hasattr(self.comm.regs, addr_str):
            print(f"{C_RED}Error:{C_RESET} Register '{C_BOLD}{addr_str}{C_RESET}' not found in csr.csv")
            print(f"Available: {C_DIM}{', '.join(self.comm.regs.__dict__.keys())}{C_RESET}")
            return None, None, None
        reg = getattr(self.comm.regs, addr_str)
        return reg.addr, addr_str, reg

    @staticmethod
    def parse_value(val_str):
        """Parse an integer or dotted-decimal IP address string to an int."""
        parts = val_str.split(".")
        if len(parts) == 4:
            octets = [int(p) for p in parts]
            if all(0 <= o <= 255 for o in octets):
                return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        return int(val_str, 0)

    @staticmethod
    def fmt_ip(value):
        """Format a 32-bit value as a dotted-decimal IP address."""
        return f"{(value >> 24) & 0xff}.{(value >> 16) & 0xff}.{(value >> 8) & 0xff}.{value & 0xff}"

    @staticmethod
    def fmt_reg(addr, value, name=None):
        """Format a register address/value pair for display."""
        # Auto-size hex width: at least 8 digits, more for wider values
        hexw = max(8, (value.bit_length() + 3) // 4) if value > 0 else 8
        ip = ""
        if name and "ip_address" in name and 0 < value <= 0xffffffff:
            ip = f" {C_DIM}({litex_netcli.fmt_ip(value)}){C_RESET}"
        if name:
            return f"{C_CYAN}{name}{C_RESET} @ {C_DIM}0x{addr:08x}{C_RESET} = {C_GREEN}0x{value:0{hexw}x}{C_RESET}{ip}"
        return f"{C_DIM}[0x{addr:08x}]{C_RESET} = {C_GREEN}0x{value:0{hexw}x}{C_RESET}"

    def cmd_read(self, tokens):
        if len(tokens) != 1:
            print(f"Usage: {C_BOLD}read{C_RESET} {C_DIM}<addr>{C_RESET}")
            return
        addr, name, reg = self.resolve_addr(tokens[0])
        if addr is None:
            return
        value = reg.read() if reg else self.comm.read(addr)
        if not self.verbose:
            hexw = max(8, (value.bit_length() + 3) // 4) if value > 0 else 8
            print(f"0x{value:0{hexw}x}")
        else:
            print(self.fmt_reg(addr, value, name))

    def cmd_write(self, tokens):
        if len(tokens) != 2:
            print(f"Usage: {C_BOLD}write{C_RESET} {C_DIM}<addr> <value>{C_RESET}")
            return
        addr, name, reg = self.resolve_addr(tokens[0])
        if addr is None:
            return
        value = self.parse_value(tokens[1])
        if reg:
            reg.write(value)
        else:
            self.comm.write(addr, value)
        readback = reg.read() if reg else self.comm.read(addr)
        if not self.verbose:
            hexw = max(8, (readback.bit_length() + 3) // 4) if readback > 0 else 8
            print(f"0x{readback:0{hexw}x}")
        else:
            hexw = max(8, (value.bit_length() + 3) // 4) if value > 0 else 8
            if name:
                print(f"{C_CYAN}{name}{C_RESET} @ {C_DIM}0x{addr:08x}{C_RESET} {C_YELLOW}<={C_RESET} {C_GREEN}0x{value:0{hexw}x}{C_RESET}")
            else:
                print(f"{C_DIM}[0x{addr:08x}]{C_RESET} {C_YELLOW}<={C_RESET} {C_GREEN}0x{value:0{hexw}x}{C_RESET}")
            print(self.fmt_reg(addr, readback, name))

    def cmd_regs(self, tokens):
        if not self.csr:
            print(f"{C_RED}Error:{C_RESET} regs requires csr")
            return
        pattern = tokens[0] if tokens else None
        for name, reg in sorted(self.comm.regs.__dict__.items(), key=lambda x: x[1].addr):
            if pattern and not fnmatch.fnmatch(name, pattern):
                continue
            value = reg.read()
            if not self.verbose:
                print(f"{name} 0x{value:08x}")
            else:
                print(f"{C_DIM}[0x{reg.addr:08x}]{C_RESET} = {C_GREEN}0x{value:08x}{C_RESET}\t{C_DIM}#{C_RESET} {C_CYAN}{name}{C_RESET}")

    def cmd_csr(self, tokens):
        if len(tokens) != 1:
            if self.csr:
                print(f"Current CSR: {C_CYAN}{self.csr}{C_RESET}")
            else:
                print(f"No CSR loaded. Usage: {C_BOLD}csr{C_RESET} {C_DIM}<file>{C_RESET}")
            return
        path = tokens[0]
        if not os.path.isfile(path):
            print(f"{C_RED}Error:{C_RESET} File not found: {C_BOLD}{path}{C_RESET}")
            return
        self.comm.close()

        self.csr = path
        self.comm = CommUDP(server=self.server, port=self.port, csr_csv=self.csr)
        self.comm.open()
        count = len(self.comm.regs.__dict__)
        if self.verbose:
            print(f"Loaded {C_GREEN}{count}{C_RESET} registers from {C_CYAN}{path}{C_RESET}")

    def execute_line(self, line):
        """Parse and execute a single command line. Returns False on quit/exit."""
        line = line.strip()
        if not line or line.startswith("#"):
            return True
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            print(f"{C_RED}Syntax error:{C_RESET} {e}")
            return True
        cmd = tokens[0].lower()
        if cmd in ("quit", "exit"):
            return False
        if cmd == "help":
            print(f"{C_BOLD}Commands:{C_RESET}")
            print(f"  {C_BOLD}read{C_RESET}  {C_DIM}<addr>{C_RESET}          Read a register (name or hex address)")
            print(f"  {C_BOLD}write{C_RESET} {C_DIM}<addr> <value>{C_RESET}  Write a register and read back")
            print(f"  {C_BOLD}regs{C_RESET}  {C_DIM}[pattern]{C_RESET}       Dump registers, optionally filtered by glob pattern")
            print(f"  {C_BOLD}csr{C_RESET}   {C_DIM}[file]{C_RESET}          Load/show CSR CSV file")
            print(f"  {C_BOLD}help{C_RESET}                  Show this help")
            print(f"  {C_BOLD}quit{C_RESET}                  Exit interactive mode")
            return True
        method = self.COMMANDS.get(cmd)
        if method is None:
            print(f"{C_RED}Unknown command:{C_RESET} {cmd}")
            return True
        getattr(self, method)(tokens[1:])
        return True

    def run_interactive(self):
        """Interactive REPL loop with readline history."""
        # Load persistent history
        try:
            readline.read_history_file(HISTORY_FILE)
        except FileNotFoundError:
            pass
        readline.set_history_length(HISTORY_LENGTH)
        atexit.register(readline.write_history_file, HISTORY_FILE)

        # Tab completion for command names, register names, and file paths
        def completer(text, state):
            buf = readline.get_line_buffer().lstrip()
            # File completion for the csr command argument
            if buf.startswith("csr "):
                path = os.path.expanduser(text)
                dirname = os.path.dirname(path) or "."
                prefix = os.path.basename(path)
                try:
                    entries = os.listdir(dirname)
                except OSError:
                    entries = []
                matches = []
                for e in sorted(entries):
                    if e.startswith(prefix):
                        full = os.path.join(dirname, e) if dirname != "." else e
                        if os.path.isdir(os.path.join(dirname, e)):
                            full += "/"
                        matches.append(full)
            elif " " not in buf:
                # First token: complete command names only
                options = list(self.COMMANDS.keys()) + ["help", "quit", "exit"]
                matches = [o for o in options if o.startswith(text)]
            elif self.csr and buf.split()[0] in ("read", "write", "regs"):
                # CSR register name completion for read/write/regs only
                matches = [n for n in sorted(self.comm.regs.__dict__.keys()) if n.startswith(text)]
            else:
                matches = []
            return matches[state] if state < len(matches) else None
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t")

        print(f"Interactive mode (type '{C_BOLD}help{C_RESET}' for commands, '{C_BOLD}quit{C_RESET}' to exit)")
        while True:
            try:
                line = input(f"{C_BOLD}litex>{C_RESET} ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not self.execute_line(line):
                break

    def run_script(self, path):
        """Execute commands from a script file."""
        with open(path) as f:
            for line in f:
                if not self.execute_line(line):
                    break


def main():
    parser = argparse.ArgumentParser(description="LiteX Etherbone/UDP register access",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--target", default="192.168.1.50:1234", help="FPGA target host[:port]")
    parser.add_argument("-c", "--csr", default=None,              help="CSR CSV file")
    parser.add_argument("-e", "--exec",        default=None,        help="Execute semicolon-delimited commands")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive command mode")
    parser.add_argument("-s", "--script",      default=None,        help="Script file to execute")

    args = parser.parse_args()

    if not args.interactive and not args.script and not getattr(args, "exec"):
        parser.print_help()
        return

    if not args.interactive:
        global C_RESET, C_BOLD, C_DIM, C_RED, C_GREEN, C_YELLOW, C_CYAN
        C_RESET = C_BOLD = C_DIM = C_RED = C_GREEN = C_YELLOW = C_CYAN = ""

    # Parse host[:port]
    if ":" in args.target:
        server, port_str = args.target.rsplit(":", 1)
        port = int(port_str)
    else:
        server = args.target
        port = 1234

    comm = CommUDP(server=server, port=port, csr_csv=args.csr)
    comm.open()

    net = litex_netcli(comm, server=server, port=port, csr=args.csr, verbose=args.interactive)

    if getattr(args, "exec"):
        for cmd in getattr(args, "exec").split(";"):
            if not net.execute_line(cmd):
                break

    if args.script:
        net.run_script(args.script)

    if args.interactive:
        net.run_interactive()

    net.close()


if __name__ == "__main__":
    main()
