Howdy y'all,

In 2002, Chris Liechti wrote a lovely little simulator for unit
testing compilers that target the MSP430, which I periodically forked
to cycle-count programs and generate slides.  I certainly owe him a
beer.

This simulator is a bit minimal, and doesn't support the MSP430X or
MSP430X2 extensions, but it's incredibly easy to hook and patch.  I've
grabbed it from its old [CVS
Repository](http://mspgcc.sourceforge.net/tools.html) on Sourceforge,
upgraded it to be compatible with Python 2.7 and GCC 4.6, but
otherwise retained Chris's original design.

73 from New York City,

--Travis Goodspeed


## Usage

The simulator is contained in `core.py` but started from a wrapper
script, such as `testing.py`.  It expecting a `logging` class for its
output, and the example writes its output to `testing.log`.  It will
print a count of failed tests, but you need to run through the log to
identify which tests failed.

The simulation can communicate with the host through a special
peripheral at `0x01b0` that takes command codes.  Additionally, a
peripheral at `0x01b1` accepts text which is printed to the log.

```
IDLE                    = 0x00
TEST_START              = 0x10
TEST_END                = 0x11
SUBTEST_START           = 0x20
SUBTEST_SUCCESS         = 0x21
SUBTEST_FAIL            = 0x22
SUBTEST_EXECUTE         = 0x2e
SUBTEST_EXECUTE_DONE    = 0x2f
```

You can of course extend this with your own peripherals, as your test
coverage grows.

## See Also

For a complete system simulator, those who don't mind Java should try
[MSPSim](http://github.com/mspsim/mspsim), which has support for many
peripherals and more modern CPU cores.

