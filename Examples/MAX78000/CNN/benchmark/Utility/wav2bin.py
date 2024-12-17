import argparse
import wave
import pyaudio  
import numpy as np
import matplotlib.pyplot as plt
import os


CHUNK = 128  # number of data points to read at a time and average for threshold
RATE = 16384  # Sampling rate
WINDOW = 16384  # number of samples to collect and send to AI85
THRESHOLD = 130  # voice detection threshold
YLIM = 10000  # Max Y value in Plots
PREAMBLE = 20 * CHUNK  # how many samples before beginning of keyword


def binvector(filename, plotenable=False, duration=10, outputfilename='', eight=False):
    """
    Goal: translates .wav file into a .bin file. Binary file holds a vector of audio, later called voiceVector.
    """
    p = pyaudio.PyAudio()  # start the PyAudio class
    sampleCount = 0
    if filename:
        print("Reading from file:" + filename + "\r\n")
        wavefile = wave.open(filename, 'rb')
        stream = p.open(format=p.get_format_from_width(wavefile.getsampwidth()),
                        channels=wavefile.getnchannels(),
                        rate=wavefile.getframerate(),
                        output=True)
        duration = 10000  # large duration for file to go to the end of file
    else:
        print("Recording from Mic \r\n")
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
        
    data = [sample := wavefile.readframes(CHUNK)]
    while sample != b'':
        data.append(sample := wavefile.readframes(CHUNK))

    
    data = np.frombuffer(b"".join(data), dtype=np.int16)
    data.tofile(outputfilename)


def convertAll(topDir, outputfile):
    """
    Walk directories from the root and convert all sample audio file to wave (.wav) files
    - skips if the file has already been converted.
    - skips if the file size is not exactly 16384.
    - returns number of files converted.
    """
    numConverted = 0
    for root, dirs, files in os.walk(topDir):
        for filename in files:
            # Full input file path
            inputFile = os.path.join(root, filename)
            
            # Construct corresponding output file path
            # (Preserve directory structure in outputDir)
            relativePath = os.path.relpath(root, topDir)  # Path relative to topDir
            outputSubdir = os.path.join(outputfile, relativePath)
            os.makedirs(outputSubdir, exist_ok=True)  # Ensure subdirectory exists
            
            # Change the filename extension to .bin for the output file
            outputFile = os.path.join(outputSubdir, os.path.splitext(filename)[0] + ".bin")
            
            # Call binvector with full paths and appropriate parameters
            binvector(filename=inputFile, plotenable=False, duration=10000, outputfilename=outputFile, eight=False)
            numConverted += 1
    return numConverted


    
# def process_directory(directory = '', plotenable=False, duration=10, outputfilename='', eight=False):
#     #if not os.path.exists(outputfilename):
#     #    os.makedirs(outputfilename)

#     for filename in os.listdir(directory):
#         if filename.lower().endswith('.wav'):
#             input_path = os.path.join(directory, filename)
#             binvector(filename, plotenable=False, duration=10, outputfilename='', eight=False)



def command_parser():
    """
    Return the argument parser
    """
    parser = argparse.ArgumentParser(description='Audio recorder command parser')
    parser.add_argument('-i', '--input', type=str, default='',
                        help='input wave file name')
    #parser.add_argument('-d', '--directory', type=str, default='',
    #                    help='Directory containing .wav files')
    parser.add_argument('-p', '--plot', action="store_true", help='Plot waves',
                        default=False)
    
    parser.add_argument('-a', '--all', required = False, action="store_true",
                        help='walk all directories and convert all files')
    parser.add_argument('-dir', '--directory', type = str, required = False, default = ".",
                        help='top directory')
    
    parser.add_argument('-d', '--duration', type=int, default=10,
                        help='Duration (sec)')
    parser.add_argument('-o', '--output', type=str, default='',
                        help='output .bin file from wav')
    parser.add_argument('-8', '--eight', action="store_true", default=False,
                        help='8 bit binary file')
    return parser.parse_args()


if __name__ == "__main__":
    command = command_parser()
    if command.all is False:
        binvector(command.input, command.plot, command.duration, command.output, command.eight)
    else:
        print(f"{convertAll(command.directory, command.output)} files are converted!")




    # ######## Do not need this, this creates c header variables #########
    # # # if an ouput header file needs to be generated
    # if outputfilename:
    #     wr = open(command.output, 'wb')
    # #     wr.write('#ifndef KWS20_TEST_VECTOR_H\n')
    # #     wr.write('#define KWS20_TEST_VECTOR_H\n\n')
    # #     if eight:
    # #         wr.write('#define EIGHT_BIT_TEST_VECTOR\n\n')
    # #     wr.write('#define KWS20_TEST_VECTOR {\\\n')



    # # create a numpy array holding a single read of audio data
    # y = np.array([])
    # w = np.empty(PREAMBLE)
    # ai85data = np.zeros((1, RATE))
    # process = False
    # word_count = 0
    # for i in range(int(duration * RATE / CHUNK)):  # number of CHUNKs for duration

    #     if filename:
    #         data = np.fromstring(wavefile.readframes(CHUNK), dtype=np.int16)
    #     else:
    #         data = np.fromstring(stream.read(CHUNK), dtype=np.int16)
    #     # data = np.linspace(CHUNK*i,CHUNK*(i+1)-1,CHUNK)

    #     if data.size < CHUNK:
    #         break
    #     # print(data.shape)

    #     # add samples to a header file
    #     if outputfilename:
    #         for point in data:
    #             if eight:
    #                 point = int(point/256)
    #             hex_point = hex(point)
    #             wr.write(b'%d' % hex_point)
    #             sampleCount += 1

    #     avg = np.average(np.abs(data))

    #     # accumulate last chunk
    #     if (not process) and (avg < THRESHOLD):
    #         # print(w[CHUNK:].shape)
    #         # print(data.shape)
    #         w = np.append(w[CHUNK:], data)

    #     if (not process) and (avg >= THRESHOLD):
    #         process = True

    #     # start reading data
    #     if process:
    #         w = np.append(w, data)
    #         if w.size >= WINDOW:
    #             process = False
    #             ww = np.append(w[:WINDOW], np.zeros((1, RATE-WINDOW)))
    #             print(ww.shape)
    #             print(ww.size)
    #             print(ai85data.shape)

    #             print('+++++++++++++++++++++++++Size of W:  ', w.size)
    #             print(w.shape)
    #             ai85data = np.vstack([ai85data, ww])
    #             word_count += 1
    #             w = w[-PREAMBLE:]

    #             # add code to send to AI85

    #     bars = "=" * int(100 * avg / 1000)
    #     peak = avg
    #     print("%04d %05d %s" % (i, peak, bars))
    #     y = np.append(y, data)

    # # close the stream gracefully
    # stream.stop_stream()
    # stream.close()
    # p.terminate()

    # print("count:", word_count)

    # # row 0 is zero
    # ai85data = np.delete(ai85data, 0, axis=0)
    # print(ai85data.shape)
    # # end created header file
    # if outputfilename:
    #     # add zeros to the end to make it 16384
    #     if sampleCount < WINDOW:
    #         for i in range(WINDOW-sampleCount):
    #             wr.write(b'\x00')
    #             sampleCount += 1
    #     # wr.write('} \n')
    #     # wr.write('#define KWS20_TEST_VECTOR_SIZE ')
    #     # wr.write(sampleCount.__str__())
    #     # wr.write('\n')
    #     # wr.write('#endif \n')
    #     wr.close()

    # if not plotenable:
    #     return

    # # plot data
    # x = range(y.size)
    # if word_count == 0:
    #     word_count = 1  # to plot the main one at least

    # grid = plt.GridSpec(2, word_count, wspace=0.2, hspace=0.2)

    # # complete waveform
    # plt.subplot(grid[0, :])
    # plt.title('Complete Waveform')
    # plt.ylim([-YLIM, YLIM])
    # plt.grid(True)
    # plt.grid(color='b', ls='-.', which='both', lw=0.25, animated=True)
    # plt.plot(x, y, color='red')

    # # individual plots if there is any keyword data captured
    # if ai85data.shape[0] > 0:
    #     for i in range(0, word_count):
    #         plt.subplot(grid[1, i])
    #         plt.title('#:' + (i + 1).__str__())
    #         plt.ylim([-YLIM, YLIM])
    #         plt.plot(range(RATE), ai85data[i, :])
    #         # print(ai85data[i, :].shape)
    # plt.show()

# def binvectors(filename='', plotenable=False, duration=10, outputfilename='', eight=False):
#     """
#     Captures audio from wav file, converts to binary file.
#     """
#     p = pyaudio.PyAudio()  # start the PyAudio class
#     sampleCount = 0
#     with open(outputfilename, 'wb') as binary_file:
#         if filename:
#             print("Reading from file:" + filename + "\r\n")
#             wavefile = wave.open(filename, 'rb')
#             stream = p.open(format=p.get_format_from_width(wavefile.getsampwidth()),
#                             channels=wavefile.getnchannels(),
#                             rate=wavefile.getframerate(),
#                             output=True)
#             duration = 10000  # large duration for file to go to the end of file
#         else:
#             print("Recording from Mic \r\n")
#             stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True,
#                             frames_per_buffer=CHUNK)

#         # create a numpy array holding a single read of audio data
#         y = np.array([])
#         w = np.empty(PREAMBLE)
#         ai85data = np.zeros((1, RATE))
#         process = False
#         word_count = 0

#         for i in range(int(duration * RATE / CHUNK)):
#             if filename:
#                 data = np.frombuffer(wavefile.readframes(CHUNK), dtype=np.int16)
#             else:
#                 data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
#             if data.size < CHUNK:
#                 break
#             binary_file.write(data.tobytes())
#             sampleCount += len(data)

#             avg = np.average(np.abs(data))

#             # accumulate last chunk
#             if (not process) and (avg < THRESHOLD):
#                 w = np.append(w[CHUNK:], data)

#             if (not process) and (avg >= THRESHOLD):
#                 process = True

#             # start reading data
#             if process:
#                 w = np.append(w, data)
#                 if w.size >= WINDOW:
#                     process = False
#                     ww = np.append(w[:WINDOW], np.zeros((1, RATE-WINDOW)))
#                     ai85data = np.vstack([ai85data, ww])
#                     word_count += 1
#                     w = w[-PREAMBLE:]

#             bars = "=" * int(100 * avg / 1000)
#             peak = avg
#             print("%04d %05d %s" % (i, peak, bars))
#             y = np.append(y, data)

#         stream.stop_stream()
#         stream.close()
#         p.terminate()

#         print("count:", word_count)

#         # row 0 is zero
#         ai85data = np.delete(ai85data, 0, axis=0)
#         print(ai85data.shape)

#         # Write processed data to the binary file
#         for row in ai85data:
#             row.tofile(binary_file)

#         # Ensure that the binary file contains 16384 samples
#         while sampleCount < 16384:
#             binary_file.write(b'\x00\x00')
#             sampleCount += 1

#         if not plotenable:
#             return

#         # Plot data
#         x = range(y.size)
#         if word_count == 0:
#             word_count = 1  # to plot the main one at least

#         grid = plt.GridSpec(2, word_count, wspace=0.2, hspace=0.2)

#         # complete waveform
#         plt.subplot(grid[0, :])
#         plt.title('Complete Waveform')
#         plt.ylim([-YLIM, YLIM])
#         plt.grid(True)
#         plt.grid(color='b', ls='-.', which='both', lw=0.25, animated=True)
#         plt.plot(x, y, color='red')

#         # individual plots if there is any keyword data captured
#         if ai85data.shape[0] > 0:
#             for i in range(0, word_count):
#                 plt.subplot(grid[1, i])
#                 plt.title('#:' + (i + 1).__str__())
#                 plt.ylim([-YLIM, YLIM])
#                 plt.plot(range(RATE), ai85data[i, :])
#         plt.show()

