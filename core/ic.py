from unicorn.arm_const import *
import struct
from .logger import logger

ARM_CTX_REGISTERS = [
    UC_ARM_REG_XPSR,
    UC_ARM_REG_PC,
    UC_ARM_REG_LR,
    UC_ARM_REG_R12,
    UC_ARM_REG_R3,
    UC_ARM_REG_R2,
    UC_ARM_REG_R1,
    UC_ARM_REG_R0,
]

ARMCTX_EXTRA_REGISTERS = [
    UC_ARM_REG_FPSCR,
    UC_ARM_REG_S15,
    UC_ARM_REG_S14,
    UC_ARM_REG_S13,
    UC_ARM_REG_S12,
    UC_ARM_REG_S11,
    UC_ARM_REG_S10,
    UC_ARM_REG_S9,
    UC_ARM_REG_S8,
    UC_ARM_REG_S7,
    UC_ARM_REG_S6,
    UC_ARM_REG_S5,
    UC_ARM_REG_S4,
    UC_ARM_REG_S3,
    UC_ARM_REG_S2,
    UC_ARM_REG_S1,
    UC_ARM_REG_S0,
]

def interrupt_enter(irq_num, uc, fw_base_addr):
    # read handler address from vector table
    vector_addr = (irq_num * 4) + fw_base_addr
    data = uc.mem_read(vector_addr, 4)
    handler_addr = struct.unpack('<I', data)[0]
    control = uc.reg_read(UC_ARM_REG_CONTROL)
    spsel_bit = (control & 0b10 == 0b10)
    fpca_bit = (control & 0b100 == 0b100)   
    # save registers
    #print("before saving context")
    #dump_ctx_registers(uc)
    save_context(uc, spsel_bit, fpca_bit)
    # put magic value in LR and call handler
    lr = 0xffffffe9
    if spsel_bit:
        lr |= 0b100
    if not fpca_bit:
        lr |= 0b10000
    uc.reg_write(UC_ARM_REG_LR, lr)
    uc.reg_write(UC_ARM_REG_IPSR, irq_num)
    uc.reg_write(UC_ARM_REG_PC, handler_addr)
    logger.info("[*] entering interrupt %d, spsel=%r fpca=%r handler_addr=0x%x sp=0x%x", irq_num, spsel_bit, fpca_bit, handler_addr, uc.reg_read(UC_ARM_REG_SP))

def interrupt_return(uc):
    lr = uc.reg_read(UC_ARM_REG_LR)
    irq_num = uc.reg_read(UC_ARM_REG_IPSR)
    if lr & 0xffffff00 == 0xffffff00:
        spsel = (lr & 0b100 != 0)
        fpca = (lr & 0b10000 == 0)
        restore_context(uc, spsel, fpca)
        #print("after restoring context")
        #dump_ctx_registers(uc)
        pc = uc.reg_read(UC_ARM_REG_PC)
        sp = uc.reg_read(UC_ARM_REG_SP)
        logger.info("[*] returning from interrupt %d spel=%r fpca=%r lr=%x pc=0x%x sp=0x%x", irq_num, spsel, fpca, lr, pc, sp)
        # set control register
        ctrl = 0
        if spsel:
            ctrl |= 0b10
        if fpca:
            ctrl |= 0b100
        uc.reg_write(UC_ARM_REG_CONTROL, ctrl)
    else:
        control = uc.reg_read(UC_ARM_REG_CONTROL)
        spsel_bit = (control & 0b10 == 0b10)
        fpca_bit = (control & 0b100 == 0b100)
        restore_context(uc, spsel_bit, fpca_bit)
        #print("after restoring context")
        #dump_ctx_registers(uc)
        pc = uc.reg_read(UC_ARM_REG_PC)
        sp = uc.reg_read(UC_ARM_REG_SP)
        logger.info("[*] returning from interrupt %d pc=0x%x sp=0x%x", irq_num, pc, sp)        

def save_context(uc, spsel_bit, fpca_bit):
    sp_reg = UC_ARM_REG_MSP
    if spsel_bit:
        sp_reg = UC_ARM_REG_PSP
    
    sp = uc.reg_read(sp_reg)
    if fpca_bit:
        #print("saving extended registers")
        for reg in ARMCTX_EXTRA_REGISTERS:
            val = uc.reg_read(reg)
            sp -= 4
            uc.mem_write(sp, val.to_bytes(4, 'little'))
    for reg in ARM_CTX_REGISTERS:
        val = uc.reg_read(reg)
        sp -= 4
        uc.mem_write(sp, val.to_bytes(4, 'little'))
    
    uc.reg_write(UC_ARM_REG_SP, sp)

def restore_context(uc, spsel, fpca):
    sp_reg = UC_ARM_REG_MSP
    if spsel:
        sp_reg = UC_ARM_REG_PSP        
    sp = uc.reg_read(sp_reg)    
    for reg in ARM_CTX_REGISTERS[::-1]:
        data = uc.mem_read(sp, 4)
        val = struct.unpack('<I', data)[0]
        sp += 4
        uc.reg_write(reg, val)
    if fpca:
        #print("restoring extended registers")
        for reg in ARMCTX_EXTRA_REGISTERS[::-1]:
            data = uc.mem_read(sp, 4)
            val = struct.unpack('<I', data)[0]
            sp += 4
            uc.reg_write(reg, val)

    uc.reg_write(UC_ARM_REG_SP, sp)
   
def dump_ctx_registers(uc):
    for reg in ARM_CTX_REGISTERS:
        logger.debug("%s %x", reg, uc.reg_read(reg))
