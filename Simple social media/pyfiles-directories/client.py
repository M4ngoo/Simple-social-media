import random
import socket
import threading
import os
import win32gui
import time

event = threading.Event()

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

ip = socket.gethostbyname(socket.gethostname())
port = 55555

client.connect((ip, port))

abspath = os.getcwd()
path = abspath + r"\client_logs"

search = False
chunks = []

if not os.path.exists(path): #creates the client logs folder if it doen't exist
    os.mkdir(path)

def help_func(): #checks if the user's username and password are correct 
    username_message = client.recv(1024).decode("utf-8")
    print(username_message)
    while True:
        answer = input("")
        if not answer:
            print("wrong input")
            continue
        if answer.count(" ") >= 1:
            print("no spaces allowed")
            continue
        if len(answer) < 5:
            print("the username is too short")
            continue
        if len(answer) > 16:
            print("the username is too long")
            continue
        client.send(answer.encode("utf-8"))
        break
    password_message = client.recv(1024).decode("utf-8")
    print(password_message)
    while True:
        answer = input("")
        if not answer:
            print("wrong input")
            continue
        if answer.count(" ") >= 1:
            print("no spaces allowed")
            continue
        if len(answer) < 5:
            print("the password is too short")
            continue
        if len(answer) > 30:
            print("the password is too long")
            continue
        client.send(answer.encode("utf-8"))
        break

def signuphandler(): #creates an account and also creates the followers/following txt files and the directory folder if it doen't exist 
    flag = False
    while not flag:
        help_func()
        message = client.recv(1024).decode("utf-8")
        print(message)
        if not message.startswith("Username already"):
            flag = True
    if message.startswith("Welcome"):
        followingpath = path + "\\" + message[8:-1] + "following.txt"
        followerspath = path + "\\" + message[8:-1] + "followers.txt"
        userdirectory = path + "\\" + message[8:-1] + "Directory"
        userdownloaddirectory = path + "\\" + message[8:-1] + "DownloadDirectory"
        with open(followingpath, "a+") as f:
            pass
        with open(followerspath, "a+") as f:
            pass
        if not os.path.exists(userdirectory):
            os.mkdir(userdirectory)
        if not os.path.exists(userdownloaddirectory):
            os.mkdir(userdownloaddirectory)
        
#the user chooses to login or signup
message = client.recv(1024).decode("utf-8")
print(message)
while True:
    answer = input("")
    if answer.isnumeric():
        if int(answer) == 1 or int(answer) == 2:
            client.send(answer.encode("utf-8"))
            break
        else:
            print("wrong input!")
            continue
    else:
        print("wrong input!")
        continue

if answer == "1":
    while True:
        help_func()
        message = client.recv(1024).decode("utf-8")
        print(message)
        if message.startswith("Welcome"):
            break
        if message.startswith("No user"):
            while True:
                answer = input("")
                if answer.lower() == "y" or answer.lower() == "n":
                    client.send(answer.encode("utf-8"))
                    break
                print("Wrong input!")
            if answer == "y":
                signuphandler()
                break
        
if answer == "2":
    signuphandler()

def receive():
    while True:
        global search, chunks
        try: #if the client receives this message it is getting ready to download an image 
            msg_recieved = client.recv(1024).decode("utf-8")
            if msg_recieved.startswith("IMAGE a54623f43d"):
                thisuser = msg_recieved.split(" ")[2]
                with open(path + "\\" + thisuser + "DownloadDirectory" + "\\" + "IMG_" + str(random.randint(1000, 9999)) + ".jpg", "wb+") as f:
                    image_chunk = client.recv(2048)
                    while image_chunk:
                        f.write(image_chunk)
                        client.settimeout(1)
                        image_chunk = client.recv(2048)
            elif msg_recieved.startswith("IMAGE a453jafe2d "):
                search = True
                acks = 1
                thisuser = msg_recieved.split(" ")[2]
                chunks.append(thisuser)
                size = msg_recieved.split(" ")[3]
                image_chunk = client.recv(int(int(size)/10)) #receives 1/10th of the file in total ~10 packets
                while image_chunk:
                    chunks.append(image_chunk)
                    if len(chunks) != 3 and len(chunks) != 6:
                        client.send("ACK 0".encode("utf-8")) if acks == 1 else client.send("ACK 1".encode("utf-8"))
                        if acks == 1:
                            acks = 0
                        else:
                            acks = 1
                    if len(chunks) == 3: #doesn't send ack for 3rd packet
                        client.settimeout(4)
                        print(client.recv(1024).decode("utf-8"))
                    if len(chunks) == 6: #sends ack for 3rd packet after a delay enough to cause a timeout
                        time.sleep(3)
                        client.settimeout(4)
                        print(client.recv(1024).decode("utf-8"))
                    client.settimeout(1)
                    image_chunk = client.recv(int(int(size)/10))
            elif msg_recieved.startswith("sdj42sdfg3 Choose an image"): #this is the upload message
                flag = False
                username = msg_recieved[37:]
                while True:
                    try:
                        tempfile = win32gui.GetOpenFileNameW() #opens the file explorer
                        os.chdir(abspath) #the file explorer changes the working directory so we change it back
                    except:
                        tempfile = None
                    if not tempfile:
                        flag = True
                        client.send("STOP jk6gtj4isw".encode("utf-8")) #if the user chooses nothing then they send to the server this message to terminate the upload
                        event.set() #signals the thread event to unpause the input function
                        event.clear() #signals the thread event to stop the input function again for future uploads
                        break
                    elif "client_logs" in tempfile[0]: 
                        continue
                    else:
                        break
                if not flag:
                    caption = input("Caption: ") #the user writes a caption
                    with open(tempfile[0], "rb") as f:
                        temp = f.read()
                    with open(path + "\\" + username + "Directory" + "\\" + tempfile[0].split("\\")[-1], "wb+") as f:
                        f.write(temp) 
                    with open(path + "\\" + username + "Directory" + "\\" + tempfile[0].split("\\")[-1], "a") as f:
                        f.write("\nendofphoto\n" + caption)  
                    client.send(tempfile[0].encode("utf-8")) 
                    with open(path + "\\" + username + "Directory" + "\\" + tempfile[0].split("\\")[-1], "rb") as f:
                        image_data = f.read(2048)
                        while image_data:
                            client.send(image_data)
                            image_data = f.read(2048)
                    event.set()
                    event.clear()
            elif msg_recieved.startswith("acceptinit "): #writes the other user's name to the user's followers txt file
                thisuser = msg_recieved.split(" ")[1]
                otheruser = msg_recieved.split(" ")[2]
                with open(path + "\\" + thisuser + "followers.txt", "r") as f:   
                    followers = f.read()
                followers += f"{otheruser} "
                with open(path + "\\" + thisuser + "followers.txt", "w") as f:
                    f.writelines(followers) 
                print("Accepted follow request!")  
            elif msg_recieved.startswith("addtofollowing "): #writes the other user's name to the user's following txt file
                thisuser = msg_recieved.split(" ")[1]
                otheruser = msg_recieved.split(" ")[2]
                with open(path + "\\" + thisuser + "following.txt", "r") as f:
                    following = f.read()
                following += f"{otheruser} "
                with open(path + "\\" + thisuser + "following.txt", "w") as f:
                    f.writelines(following)
                print(f"{otheruser} has accepted your follow request!")
            elif msg_recieved.startswith("unfollowinit "): #deletes the other user's name to the user's following txt file
                thisuser = msg_recieved.split(" ")[1]
                otheruser = msg_recieved.split(" ")[2]
                with open(path + "\\" + thisuser + "following.txt", "r") as f:
                    following = f.read()
                if following.startswith(otheruser):
                    following = following.replace(f"{otheruser} ", "")
                else:
                    following = following.replace(f" {otheruser}", "")
                with open(path + "\\" + thisuser + "following.txt", "w") as f:
                    f.writelines(following)
            elif msg_recieved.startswith("removefromfollowers "): #deletes the other user's name to the user's followers txt file
                thisuser = msg_recieved.split(" ")[1]
                otheruser = msg_recieved.split(" ")[2]
                with open(path + "\\" + thisuser + "followers.txt", "r") as f:
                    followers = f.read()
                if followers.startswith(otheruser):
                    followers = followers.replace(f"{otheruser} ", "")
                else:
                    followers = followers.replace(f" {otheruser}", "")
                with open(path + "\\" + thisuser + "followers.txt", "w") as f:
                    f.writelines(followers)
            elif msg_recieved.startswith("showfollowing"): #returns the users that this user is following
                thisuser = msg_recieved.split(" ")[1]
                with open(path + "\\" + thisuser + "following.txt", "r") as f:
                    following = f.read()
                    following = following.split(" ")
                print("\n".join(following))
            elif msg_recieved.startswith("showfollowers"): #returns the users that follow this user
                thisuser = msg_recieved.split(" ")[1]
                with open(path + "\\" + thisuser + "followers.txt", "r") as f:
                    followers = f.read()
                    followers = followers.split(" ")
                print("\n".join(followers))
            elif msg_recieved.startswith("syncfollowers aeflq3452d"): #synchronises this user's followers
                thisuser = msg_recieved.split(" ")[2]
                syncfollowers = msg_recieved.split(" ")[3:-1]
                syncfollowers = [x + " " for x in syncfollowers]
                with open(path + "\\" + thisuser + "followers.txt", "w") as f:
                    f.writelines(syncfollowers)
            elif msg_recieved.startswith("syncfollowing aeflq3452d"): #synchronises this user's following
                thisuser = msg_recieved.split(" ")[2]
                syncfollowing = msg_recieved.split(" ")[3:-1]
                syncfollowing = [x + " " for x in syncfollowing]
                with open(path + "\\" + thisuser + "following.txt", "w") as f:
                    f.writelines(syncfollowing)
            else:
                print(msg_recieved)
        except TimeoutError:
            client.settimeout(None)
            if search:
                chunks.remove(chunks[2])
                chunks.remove(chunks[5])
                with open(path + "\\" + chunks[0] + "DownloadDirectory" + "\\" + "IMG_" + str(random.randint(1000, 9999)) + ".jpg", "wb") as f:
                    for x in chunks[1:]:
                        f.write(x)
                search = False
                chunks = []
            continue
        except:
            print("The server crashed!")
            client.close()
            break

def send_msg():
    while True:
        message = input("")
        client.send(message.encode("utf-8"))
        if message == "/upload":
            event.wait() #if the user types /upload then he is unable to type until he chooses an image to upload or chooses nothing

receive_thread = threading.Thread(target=receive)
receive_thread.start()

send_msg_thread = threading.Thread(target=send_msg)
send_msg_thread.start()