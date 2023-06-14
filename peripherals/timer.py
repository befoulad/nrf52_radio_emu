from core.peripheral import IPeripheral, Register
import time
import threading

from core.logger import logger

class Timer_0(IPeripheral):

    def __init__(self):
        self.base_address =  0x40008000
        self.register_list = [
            Register("TASKS_START", self.base_address + 0x0),
            Register("TASKS_STOP", self.base_address + 0x4),
            Register("TASKS_CAPTURE[0]", self.base_address + 0x40),
            Register("TASKS_CAPTURE[5]", self.base_address + 0x54),
            Register("CC[0]", self.base_address + 0x540),
            Register("CC[5]", self.base_address + 0x554)
        ]
        # there are six compare/capture registers
        self.cc_registers = [0, 0, 0, 0, 0, 0]
        self.counter = 0
        self.thread = None
        self.should_stop = False
        self.populate_maps()

    def read(self, uc, address):
        if address >= self.get_reg_by_name('CC[0]').address and address <= self.get_reg_by_name('CC[5]').address:
            idx = (address - self.get_reg_by_name('CC[0]').address) // 4
            byte_array = self.cc_registers[idx].to_bytes(4, 'little')
            uc.mem_write(address, byte_array)
            #print("CC[%d] = %x" %(idx, self.cc_registers[idx]))

    def write(self, uc, address, value):
        if address == self.get_reg_by_name('TASKS_START').address:
            self.start()
        elif address == self.get_reg_by_name('TASKS_STOP').address:
            self.stop()
        if address >= self.get_reg_by_name('TASKS_CAPTURE[0]').address and address <= self.get_reg_by_name('TASKS_CAPTURE[5]').address:
            idx = (address - self.get_reg_by_name('TASKS_CAPTURE[0]').address) // 4
            self.cc_registers[idx] = self.counter * 1000000
        
    
    def get_name(self):
        return "TIMER0"
    
    def start(self):
        self.thread = threading.Thread(target=self.timer_thread)
        self.thread.start()

    def stop(self):
        if self.thread != None:
            self.should_stop = True
            self.thread.join()
        logger.info("%s timer stopped", self.get_name())

    def count(self):
        self.counter += 1
    
    def clear(self):
        self.counter = 0

    def timer_thread(self):
        timer_resolution = 1
        logger.info("%s thread started", self.get_name())
        while not self.should_stop:
            start_time = time.time()
            self.tick()
            elapsed_time = time.time() - start_time
            remaining_time = timer_resolution - elapsed_time
            if remaining_time > 0:
                time.sleep(remaining_time)
        logger.info("%s thread stopped", self.get_name())
            
    def tick(self):
        self.counter += 1