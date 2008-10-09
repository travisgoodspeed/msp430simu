COPT= -mmcu=msp430x135 -O2

all:    testing_example.a43 force
	./testing.py testing_example.a43

testing_example.a43: testing_example.elf
	msp430-objcopy -O ihex $< $@
	#msp430-objdump -DS $< >testing.dump.txt

testing_example.elf: testing_example.c
	msp430-gcc ${COPT} -o $@ $<
	msp430-gcc ${COPT} -S $< >/dev/null

CPU=msp430x149
COPT= -mmcu=${CPU} -O2
ASMOPT= -mmcu=${CPU}

hwmultest.a43: hwmultest.elf
	msp430-objcopy -O ihex $< $@

hwmultest.elf: hwmultest.o hwmul32.o
	msp430-gcc -mmcu=${CPU} -o $@ $^

hwmultest.o: hwmultest.c
	msp430-gcc ${COPT} -c $<
	msp430-gcc ${COPT} -S $< >/dev/null

hwmultest: hwmultest.a43 force
	./testing.py hwmultest.a43

hwmul32.o: hwmul32.s
	msp430-gcc -x assembler-with-cpp ${ASMOPT} -o $@ -c $<

clean:
	rm -f testing_example.elf testing_example.a43 testing_example.o
        
.PHONY: force
force: