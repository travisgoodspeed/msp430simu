COPT= -mmcu=msp430x135 -O2

all:    testing_example.a43 force
	./testing.py testing_example.a43

testing_example.a43: testing_example.elf
	msp430-objcopy -O ihex $< $@
	#msp430-objdump -DS $< >testing.dump.txt

testing_example.elf: testing_example.c
	msp430-gcc ${COPT} -o $@ $<
	msp430-gcc ${COPT} -S $< >/dev/null


COPT= -mmcu=msp430x149 -O2
hwmultest.a43: hwmultest.elf
	msp430-objcopy -O ihex $< $@

hwmultest.elf: hwmultest.c
	msp430-gcc ${COPT} -o $@ $<
	msp430-gcc ${COPT} -S $< >/dev/null

hwmultest: hwmultest.a43 force
	./testing.py hwmultest.a43


clean:
	rm -f testing_example.elf testing_example.a43 testing_example.o
        
.PHONY: force
force: