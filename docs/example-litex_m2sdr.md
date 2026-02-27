# Example: LiteX M.2 SDR

This guide shows how to use `litex_netcli.py` with the
[LiteX M.2 SDR](https://github.com/enjoy-digital/litex_m2sdr) board and an
[Acorn Baseboard Mini](https://enjoy-digital-shop.myshopify.com/products/litex-acorn-baseboard-mini).

## Hardware Prerequisites

- 1.25G SFP-T Transceiver (1000BASE-T Rj45 Copper Module)
- USB-Fan for cooling LiteX
- USB-Cable for connecting to the baseboard JTAG interface
- [Rectangular Cable Assemblies PicoEZmate 6 Circuit 50MM](https://eu.mouser.com/ProductDetail/538-36920-0600) for connecting the baseboard's USB-JTAG interface to the M.2 SDR.
- Adjust [jumpers on the Acorn Baseboard Mini](https://github.com/enjoy-digital/litex_m2sdr/blob/main/doc/litex_acorn_baseboard_mini_schematic.pdf):
    - Jumper on JP2 between pins 1-2
    - Jumper on JP3 between pins 1-2

## Firmware

Install the [latest litex_m2sdr_baseboard_eth_*.zip bitstream](https://github.com/meriac/litex_m2sdr/releases) using [OpenFPGALoader](https://github.com/trabucayre/openFPGALoader):

```bash
# Flash the default image of the M.2 SDR
openFPGALoader --fpga-part xc7a200tsbg484 --cable ft4232 -o 0x00000000 -f litex_m2sdr_baseboard_eth_fallback.bin --verify

# Flash the fall-back image of the M.2 SDR in case the active image crashes,
# potentially bricking further updates over serial/PCIe
openFPGALoader --fpga-part xc7a200tsbg484 --cable ft4232 -o 0x00800000 -f litex_m2sdr_baseboard_eth_operational.bin --verify
```

Copy the `csr.csv` from the zip archive to this tool's directory.

## Example Session

Start the interactive REPL with the M.2 SDR's CSR file:

```bash
./litex_netcli.py -c csr.csv -i
```

### Read and write registers

```
litex> read ctrl_scratch
ctrl_scratch @ 0x00000004 = 0x12345678
litex> write ctrl_scratch 0xdeadbeef
ctrl_scratch @ 0x00000004 <= 0xdeadbeef
ctrl_scratch @ 0x00000004 = 0xdeadbeef
```

### Read XADC sensors

```
litex> regs xadc_*
[0x00002000] = 0x000009ed	# xadc_temperature
[0x00002004] = 0x00000556	# xadc_vccint
[0x00002008] = 0x00000988	# xadc_vccaux
[0x0000200c] = 0x00000557	# xadc_vccbram
[0x00002010] = 0x00000001	# xadc_eoc
[0x00002014] = 0x00000001	# xadc_eos
```

### Inspect AD9361 registers

```
litex> regs ad9361_*
[0x0000c000] = 0x00000003	# ad9361_config
[0x0000c004] = 0x00000000	# ad9361_ctrl
[0x0000c008] = 0x00000018	# ad9361_stat
[0x0000c00c] = 0x00000000	# ad9361_bitmode
[0x0000c010] = 0x00001801	# ad9361_spi_control
[0x0000c014] = 0x00000001	# ad9361_spi_status
[0x0000c018] = 0x00000500	# ad9361_spi_mosi
[0x0000c01c] = 0x00ffff21	# ad9361_spi_miso
[0x0000c020] = 0x00000000	# ad9361_phy_control
[0x0000c024] = 0x00000000	# ad9361_prbs_tx
[0x0000c028] = 0x00000000	# ad9361_prbs_rx
...
```

### Configure streaming IP address

Dotted-decimal IP notation can be used as a value for any register write — it is
converted to a 32-bit integer (`192.168.1.100` becomes `0xc0a80164`). On
read-back, registers whose name contains `ip_address` automatically display the
dotted-decimal form alongside the hex value:

```
litex> write eth_rx_streamer_ip_address 192.168.1.100
eth_rx_streamer_ip_address @ 0x00007804 <= 0xc0a80164
eth_rx_streamer_ip_address @ 0x00007804 = 0xc0a80164 (192.168.1.100)
```

### Interactive vs non-interactive output

Without `-i`, output is bare values for easy parsing. With `-i`, output includes
addresses, ANSI colors, and register names:

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
