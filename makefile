COPT= -mmcu=msp430x149 -O2

all:    testing_example.a43 force
	./testing.py testing_example.a43

testing_example.a43: testing_example.elf
	msp430-objcopy -O ihex $< $@
	#msp430-objdump -DS $< >testsing.dump.txt

testing_example.elf: testing_example.c
	msp430-gcc ${COPT} -o $@ $<
	#msp430-gcc ${COPT} -S $<

clean:
	rm -f testing_example.elf testing_example.a43 testing_example.o
        
.PHONY: force
force: