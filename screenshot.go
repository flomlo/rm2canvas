package main

import (
	"encoding/binary"
	"image"
	"image/png"
	"io"
	"log"
	"os"
)

const (
	screenWidth  = 1872
	screenHeight = 1404
	fbAddress    = 4387048
)

func main() {

	file, err := os.OpenFile(os.Args[1], os.O_RDONLY, os.ModeDevice)
	if err != nil {
		log.Fatal("cannot open file: ", err)
	}
	defer file.Close()
	addr, err := getPointer(file, fbAddress)
	if err != nil {
		log.Fatal(err)
	}
	log.Println("Address is: ", addr)
	img, err := getImage(file, addr)
	f, err := os.Create("image.png")
	if err != nil {
		log.Fatal(err)
	}

	if err := png.Encode(f, img); err != nil {
		f.Close()
		log.Fatal(err)
	}

	if err := f.Close(); err != nil {
		log.Fatal(err)
	}
}

func getPointer(r io.ReaderAt, offset int64) (int64, error) {
	pointer := make([]byte, 4)
	_, err := r.ReadAt(pointer, offset)
	if err != nil {
		return 0, err
	}
	return int64(binary.LittleEndian.Uint32(pointer)), nil
}

func getImage(r io.ReaderAt, offset int64) (image.Image, error) {
	pixels := make([]byte, screenHeight*screenWidth)
	_, err := r.ReadAt(pixels, offset)
	if err != nil {
		return nil, err
	}
	img := &image.Gray{
		Pix:    pixels,
		Stride: screenWidth,
		Rect:   image.Rect(0, 0, screenWidth, screenHeight),
	}
	return img, nil
}
