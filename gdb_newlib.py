try:
    import gdb
except ImportError:
    error_str = """
    This script can only be run within gdb!
    You need to 'source gdb_newlib.py' from (gdb) or in your init file
    """
    raise Exception(error_str)

from prettytable import PrettyTable


class NewlibCommand(gdb.Command):
    """Utility commands for debugging newlib"""

    def __init__(self):
        super(NewlibCommand, self).__init__(
                'newlib', gdb.COMMAND_USER, gdb.COMPLETE_NONE, prefix=True)

    def invoke(self, arg, from_tty):
        gdb.execute('help newlib')
NewlibCommand()


class NewlibDefaultHeapDump(gdb.Command):
    """Prints the current blocks in a newlib heap

    Newlib uses a heap implementaion written by Doug Lea. You can find the implementation as part
    of the newlib sources here:
        https://github.com/bminor/newlib/blob/master/newlib/libc/stdlib/mallocr.c#L11

    This python-gdb utility command attempts to print all the malloc_chunk's that currently make up
    the heap in an easy to read format. This can be useful to get a better understanding of
    fragmentation and free space

    Note: The function currently assumes you are linking newlib with debug so it can find the
    following symbol information:
         * '__malloc_sbrk_base' static
         * '__malloc_av_' static
         * 'struct malloc_chunk' type

    This could probably be improved in the future by also allowing a user to specify this info via
    command args and loading the 'struct malloc_chunk' symbol definition into gdb as part of a
    dummy elf
    """
    def __init__(self):
        super(NewlibDefaultHeapDump, self).__init__('newlib heapdump', gdb.COMMAND_USER)

    def invoke(self, unicode_args, from_tty):
        results = PrettyTable()
        results.field_names = list(['Block Addr', 'User Data Start', 'Tot Size (bytes)'])

        heap_start = gdb.parse_and_eval('__malloc_sbrk_base')

        malloc_chunk_ptr_type = gdb.lookup_type("struct malloc_chunk").pointer()
        next_malloc_chunk_ptr = heap_start
        malloc_chunk = next_malloc_chunk_ptr.cast(malloc_chunk_ptr_type)
        running_total = 0
        bytes_free = 0
        blocks_allocated = 0

        top_bin = gdb.parse_and_eval('__malloc_av_[2]')

        while True:
            flags = malloc_chunk['size'] & 0x3
            block_size = malloc_chunk['size'] & ~0x3
            running_total += block_size
            next_malloc_chunk_ptr += block_size
            next_malloc_chunk = next_malloc_chunk_ptr.cast(malloc_chunk_ptr_type)
            blocks_allocated += 1

            # Check the PREV_INUSE flag to figure out if the current block is free
            in_use = next_malloc_chunk['size'] & 0x1
            user_data = '0x%x' % malloc_chunk['fd'].address if in_use else 'FREE'
            bytes_free += block_size if not in_use else 0

            results.add_row([str(malloc_chunk), user_data, str(block_size)])

            if top_bin == malloc_chunk:  # We are done
                break
            malloc_chunk = next_malloc_chunk

        print(results)
        print("%d blocks: %d/%d bytes free" % (blocks_allocated, bytes_free, running_total))

NewlibDefaultHeapDump()
