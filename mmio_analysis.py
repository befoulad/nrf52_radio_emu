from cmsis_svd.parser import SVDParser

def load_mmio_register_addr_list():
    registers = []
    with open('data/mmio.txt', 'r') as fp:
        lines = fp.readlines()
        count = 0
        for line in lines:
            count += 1
            mmio_addr = int(line.strip(),16)
            registers.append(mmio_addr)
        print("read %d lines" %count)
    return registers


addresses = load_mmio_register_addr_list()
unmatched_addresses = set()
matched_mmio_registers = {}
parser = SVDParser.for_xml_file('data/nrf52840.svd')
device = parser.get_device()
for addr in addresses:    
    found = False
    for p in device.peripherals:
        max_addr = p.base_address + p.address_block.offset + p.address_block.size
        if addr >= p.base_address and addr <= max_addr:
            if p.name not in matched_mmio_registers.keys():
                matched_mmio_registers[p.name] = []
            matched_mmio_registers[p.name].append(addr)
            print("%x -> %s" %(addr, p.name))
            found = True
            break
    if not found:
        unmatched_addresses.add(addr)

print(matched_mmio_registers.keys())
print("unamtched addresses:")
for addr in unmatched_addresses:
    print("%x" %addr)