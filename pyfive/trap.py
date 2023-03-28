from enum import Enum

class EXCEPTION(Enum):
    InstructionAddressMisaligned = 0
    InstructionAccessFault = 1
    IllegalInstruction = 2
    Breakpoint = 3
    LoadAddressMisaligned = 4
    LoadAccessFault = 5
    StoreAMOAddressMisaligned = 6
    StoreAMOAccessFault = 7
    EnvironmentCallFromUMode = 8
    EnvironmentCallFromSMode = 9
    EnvironmentCallFromMMode = 11
    InstructionPageFault = 12
    LoadPageFault = 13
    StoreAMOPageFault = 15

class INTERRUPT(Enum):
    UserSoftwareInterrupt        = 0
    SupervisorSoftwareInterrupt  = 1
    MachineSoftwareInterrupt     = 3
    UserTimerInterrupt           = 4
    SupervisorTimerInterrupt     = 5
    MachineTimerInterrupt        = 7
    UserExternalInterrupt        = 8
    SupervisorExternalInterrupt  = 9
    MachineExternalInterrupt     = 11

