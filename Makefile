run:
	git submodule update --init --recursive
	cd xv6-riscv && make && riscv64-unknown-elf-objcopy -O binary kernel/kernel  kernel && make fs.img
	export PYTHONPATH=`pwd`/pyfive:${PYTHONPATH}
	python3 pyfive/cli.py xv6-riscv/kernel xv6-riscv/fs.img
test:
	pytest -s .
