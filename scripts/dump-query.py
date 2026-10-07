"""Fixed drgn queries. No user programs, live kernel access, or arbitrary expressions."""
import sys
import drgn
from drgn.helpers.linux.pid import for_each_task

program=drgn.Program()
program.set_core_dump(sys.argv[1])
program.load_debug_info([sys.argv[2]],default=False,main=False)
print('KERNEL_RELEASE',program['init_uts_ns'].name.release.string_().decode(errors='replace'))
for index,task in enumerate(for_each_task(program)):
    if index>=32:print('Task list truncated at 32');break
    print('TASK',int(task.pid),task.comm.string_().decode(errors='replace'))
