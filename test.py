import multiTumDis
import time

def main():
    print("Starting test")
    B = multiTumDis.BackendManager('../blogs')
    print(f"loaded: {B}")
    print(B.startDisplay())
    time.sleep(1)
    #B.end()
    print("Done test")

if __name__ == '__main__':
    main()
