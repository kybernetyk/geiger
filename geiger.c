#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <fcntl.h>
#include <sys/errno.h>
#include <unistd.h>
#include <termios.h>
#include <memory.h>
#include <errno.h>
#include <string.h>

int set_interface_attribs (int fd, int speed, int parity) {
        struct termios tty;
        memset (&tty, 0, sizeof tty);
        if (tcgetattr (fd, &tty) != 0) {
                fprintf(stderr, "error %d from tcgetattr", errno);
                return -1;
        }

        cfsetospeed (&tty, speed);
        cfsetispeed (&tty, speed);

        tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;     // 8-bit chars
        // disable IGNBRK for mismatched speed tests; otherwise receive break
        // as \000 chars
        tty.c_iflag &= ~IGNBRK;         // disable break processing
        tty.c_lflag = 0;                // no signaling chars, no echo,
                                        // no canonical processing
        tty.c_oflag = 0;                // no remapping, no delays
        tty.c_cc[VMIN]  = 0;            // read doesn't block
        tty.c_cc[VTIME] = 5;            // 0.5 seconds read timeout

        tty.c_iflag &= ~(IXON | IXOFF | IXANY); // shut off xon/xoff ctrl

        tty.c_cflag |= (CLOCAL | CREAD);// ignore modem controls,
                                        // enable reading
        tty.c_cflag &= ~(PARENB | PARODD);      // shut off parity
        tty.c_cflag |= parity;
        tty.c_cflag &= ~CSTOPB;
        tty.c_cflag &= ~CRTSCTS;

        if (tcsetattr (fd, TCSANOW, &tty) != 0) {
                fprintf(stderr, "error %d from tcsetattr", errno);
                return -1;
        }
        return 0;
}

void set_blocking (int fd, int should_block) {
        struct termios tty;
        memset (&tty, 0, sizeof tty);
        if (tcgetattr (fd, &tty) != 0) {
                fprintf(stderr, "error %d from tggetattr", errno);
                return;
        }

        tty.c_cc[VMIN]  = should_block ? 1 : 0;
        tty.c_cc[VTIME] = 5;            // 0.5 seconds read timeout

        if (tcsetattr (fd, TCSANOW, &tty) != 0) {
               fprintf(stderr, "error %d setting term attributes", errno);
				}
}

ssize_t ser_read(int fd, char *buf, ssize_t bufsize) {
	ssize_t r = 0;
	ssize_t accu = 0;
	char c;
	ssize_t i = 0;
	bzero(buf, bufsize);
	for (;;) {
		r = read(fd, &c, 1);
		if (r <= 0 || i >= bufsize) {
			break;
		}
		buf[i++] = c;
		accu += r;
	}
	return accu;
}

ssize_t ser_write_str(int fd, char *str) {
	return write(fd, str, strlen(str));
}

ssize_t get_version(int fd, char *buf, ssize_t bufsize) {
	ser_write_str(fd, "<GETVER>>");
	return ser_read(fd, buf, bufsize);
}

ssize_t get_serial(int fd, char *buf, ssize_t bufsize) {
	char tmp[32];
	ser_write_str(fd, "<GETSERIAL>>");
	ssize_t r = ser_read(fd, tmp, 32);
	if (r != 7) {
		memcpy(buf, "UNKNOWN", strlen("UNKNOWN"));
		return strlen("UNKNOWN");
	}
	bzero(buf, bufsize);
	for (int i = 0; i < 7; i++) {
		uint8_t byte = tmp[i];
		char *ptr = buf+(i*2);
		sprintf(ptr, "%.2X", byte);
	}
	return strlen(buf);
}

int get_cpm(int fd) {
	ser_write_str(fd, "<GETCPM>>");
	uint8_t buf[2];
	ssize_t r = ser_read(fd, (char *)buf, 2);
	return (int)buf[1];
}

int get_cps(int fd) {
	ser_write_str(fd, "<GETCPS>>");
	uint8_t buf[2];
	ssize_t r = ser_read(fd, (char *)buf, 2);
	return (int)buf[1];
}

float get_batt_voltage(int fd) {
	ser_write_str(fd, "<GETVOLT>>");
	uint8_t v;
	ssize_t r = ser_read(fd, (char *)&v, 1);
	float f = ((float)v) / 10.0f;	
	return f;
}


int main(int argc, char *argv[]) {
	char *devname = "/dev/gqgmc";
	if (argc > 1) {
		devname = strdup(argv[1]);
	}

	//O_NONBLOCK is needed on OS X if the user tries to open /dev/tty.USB... instead of /dev/cu.USB...
	//otherwise open() will hang forever
	int fd = open(devname, O_RDWR | O_NOCTTY | O_SYNC);
	if (fd == -1) {
		fprintf(stderr, "Could not open %s: %i\n", devname, errno);
		return 2;
	}
	//if it breaks try commenting out the next line
	set_interface_attribs(fd, B115200, 0);

	//this is only needed when O_NONBLOCK was used
	//if O_NONBLOCK wasn't used this will cause a hang
	//set_blocking(fd, 1);

	int show_device_info = 0;
	
	char buf[255];
	bzero(buf, 255);
	ssize_t r = 0;
	if (show_device_info) {
		r = get_version(fd, buf, 255);
		printf("Device Version:\t\t%s\n", buf);
		r = get_serial(fd, buf, 255);
		printf("Device Serial:\t\t%s\n", buf);
	}
	int cpm = get_cpm(fd);
	fprintf(stdout, "%i CPM\n", cpm);

	close(fd);
	return 0;
}
