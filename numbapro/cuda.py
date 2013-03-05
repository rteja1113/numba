import contextlib

from .cudapipeline import initialize as _initialize
from .cudapipeline.special_values import *
from .cudapipeline import driver as _driver

from .cudapipeline.decorators import jit, autojit

# NDarray device helper
@_driver.require_context
def to_device(ary, stream=0, copy=True):
    from numbapro.cudapipeline import devicearray
    devarray = ary.view(type=devicearray.DeviceNDArray)
    devarray.device_allocate(stream=stream)
    if copy:
        devarray.to_device(stream=stream)
    return devarray

@_driver.require_context
def device_array(shape, strides, dtype, order='C', stream=0):
    from numbapro.cudapipeline import devicearray
    return devicearray.DeviceArray(shape, strides, dtype, order, stream)

def device_array_like(ary, stream=0):
    order = ''
    if ary.flags['C_CONTIGUOUS']:
        order = 'C'
    elif ary.flags['F_CONTIGUOUS']:
        order = 'F'
    return device_array(ary.shape, ary.strides, ary.dtype, stream=stream)

# Stream helper
@_driver.require_context
def stream():
    from numbapro.cudapipeline.driver import Stream
    return Stream()

# Page lock
@_driver.require_context
@contextlib.contextmanager
def pinned(*arylist):
    from numbapro._utils.ndarray import ndarray_datasize
    from numbapro.cudapipeline.driver import PinnedMemory
    pmlist = []
    for ary in arylist:
        pm = PinnedMemory(ary.ctypes.data, ndarray_datasize(ary), mapped=False)
        pmlist.append(pm)
    yield
    del pmlist


@_driver.require_context
@contextlib.contextmanager
def mapped(*arylist, **kws):
    assert not kws or 'stream' in kws, "Only accept 'stream' as keyword."
    from numbapro._utils.ndarray import ndarray_datasize
    from numbapro.cudapipeline.driver import PinnedMemory
    from numbapro.cudapipeline import devicearray
    pmlist = []
    stream = kws.get('stream', 0)
    for ary in arylist:
        pm = PinnedMemory(ary.ctypes.data, ndarray_datasize(ary), mapped=True)
        pmlist.append(pm)

    devarylist = []
    for pm in pmlist:
        dptr = pm.get_device_pointer()
        devary = ary.view(type=devicearray.DeviceNDArray)
        devary.device_mapped(dptr, stream=stream)
        devarylist.append(devary)
    if len(devarylist) == 1:
        yield devarylist[0]
    else:
        yield devarylist
    del pmlist

# Device selection

def select_device(device_id):
    '''Call this before any CUDA feature is used in each thread.

        Returns a device instance

        Raises exception on error.
        '''
    from numbapro.cudapipeline import driver as cu
    driver = cu.Driver()
    device = cu.Device(device_id)
    context = driver.create_context(device)
    return device

def close():
    '''Explicitly closes the context.

        Destroy the current context of the current thread
        '''
    from numbapro.cudapipeline import driver as cu
    driver = cu.Driver()
    driver.release_context(driver.current_context())


#
# Initialize the CUDA system
#
_initialize.initialize()

