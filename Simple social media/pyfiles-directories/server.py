import socket
import threading
import random
import os
import time


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

ip = socket.gethostbyname(socket.gethostname())
port = 55555

server.bind((ip, port))
server.listen()

clients = []

path = os.getcwd()
path = path + r"\server_logs"

passpath = path + r"\user_pass.txt" 
graphpath = path + r"\SocialGraph.txt" 
userdirectory = path + r"\UserDirectory"
userdownloaddirectory = path + r"\UserDownloadDirectory"

command_ls = ["/showfollowing returns the profiles you follow.", "/showfollowers returns the profiles that follow you.",
             "/showusers returns all users", "/access_profile user_name access the prifile of the specified user (you must follow them first)", 
             "/search_image image_name returns you the specified image", "/upload allows you to upload an image to your profile", 
             "/follow user_name send a follow request to the specified user", "/unfollow user_name unfollows the specified user", 
             "/accept user_name handle the specified user's follow request (follow back, accept follow, decline follow)"]

follow_requests = {} #{user1:[user2, user3], user2:[user1]}
locked_files = []
lock = threading.Lock()

if not os.path.exists(path): #creates server_logs folder if it doen't exist
    os.mkdir(path)

if not os.path.exists(userdirectory): #creates the userdirectory folder inside server_logs if it doesn't exist
    os.mkdir(userdirectory)

if not os.path.exists(userdownloaddirectory):
    os.mkdir(userdownloaddirectory)

with open(graphpath, "a+") as f: #creates social graph txt file
    pass

with open(passpath, "a+") as f: #creates the username/passwords txt file
    pass

#---------------initialise followrequests dictionary---------------#
with open(graphpath, "r") as f:
    ls = f.readlines()

if len(ls) != 0:
    ls = [x[:-1] for x in ls]
    ls = [x.split() for x in ls]
    ls = [x[0] for x in ls]
    for user in ls:
        follow_requests[user] = []
#------------------------------------------------------------------#

#broadcasts the message to the user
def broadcast(user, message):
    for client in clients:
        if client[1] == user:
            client[0].send(message)

#searches the social graph and checks if the user exists
def search_user(user):
    with open(passpath, "r") as f:
        ls = f.readlines()
        ls = [x[:-1] for x in ls]
        ls = [x.split() for x in ls]
        ls = [x[0] for x in ls]
    if user in ls:
        return True
    return False

#searches the social graph and checks if the user follows the otheruser
def search_graph(thisuser, otheruser):
    with open(graphpath, "r") as f:
        ls = f.readlines()
        ls = [x[:-1] for x in ls]
    for graph in ls:
        if graph.startswith(otheruser) and thisuser in graph:
            return True
    return False

#accepts the follow request by writing the social graph and broadcasting the 2 users to write their following/followers files
def accept_follow(client, thisuser, otheruser):
    client.send(f"acceptinit {thisuser} {otheruser}".encode("utf-8"))
    broadcast(otheruser, f"addtofollowing {otheruser} {thisuser}".encode("utf-8"))
    with open(graphpath, "r") as f:
        ls = f.readlines()
    for x in range(len(ls)):
        if ls[x].startswith(thisuser):
            ls[x] = ls[x].replace("\n", "")
            ls[x] += f"{otheruser} \n"
    with open(graphpath, "w") as f:
        f.writelines(ls)

#help function for download images
def help_func2(client, photo_ls, username):
    client.send("\nChoose a photo you want to download or type /leave to leave the profile".encode("utf-8"))
    while True:
        answer = client.recv(1024).decode("utf-8")
        if answer == "/leave":
            break
        if answer.isnumeric():
            if int(answer) >= 1 and int(answer) <= len(photo_ls):
                client.send(f"IMAGE a54623f43d {username}".encode("utf-8")) #sends a message so the client will know it is time to receive an image
                with open(userdirectory + "\\" + photo_ls[int(answer) - 1][2] + "\\" + photo_ls[int(answer) - 1][0], "rb") as f:
                    image_data = f.read(2048)
                    while image_data:
                        client.send(image_data)
                        image_data = f.read(2048)
                with open(userdirectory + "\\" + photo_ls[int(answer) - 1][2] + "\\" + photo_ls[int(answer) - 1][0], "rb") as f:
                    image = f.read()
                with open(userdownloaddirectory + "\\" + username + "\\" + photo_ls[int(answer) - 1][0], "wb") as f:
                    f.write(image)
            else:
                client.send("Wrong number!".encode("utf-8"))
        else:
            client.send("Invalid answer!".encode("utf-8"))

#--------------------------------------------------login signup--------------------------------------------------#

#asks the client for username and password and writes them to the username/password txt file
def help_func(client):
    client.send("please enter a username (must be between 5 to 16 characters)".encode("utf-8"))
    username = client.recv(1024).decode("utf-8")
    client.send("please enter a password (must be at least 5 characters max 30)".encode("utf-8"))
    password = client.recv(1024).decode("utf-8")
    with open(passpath, "r") as f:
        temp_ls = f.readlines()
        temp_ls = [x.replace("\n", "") for x in temp_ls]
    return username, password, temp_ls

#signup a new user if the credentials already exist the program logs them in
def signup(client):
    flag = False
    flag2 = False
    while not flag2:
        flag2 = True
        username, password, temp_ls = help_func(client)
        for user_pass in temp_ls:
            user, passw = user_pass.split(" ")
            if username == user and password != passw:
                client.send("Username already exists... choose another one.".encode("utf-8"))
                flag2 = False
                break
            if username == user and password == passw:
                flag = True
                client.send(f"user already exists!\nlogging you in...\nWelcome {username}!".encode("utf-8"))
                break
    if not flag:
        with open(passpath, "a") as f:
            f.write(username + " " + password + "\n")
        with open(graphpath, "a") as f:
            f.write(username + " \n")
        if not os.path.exists(userdirectory + "\\" + username):
            os.mkdir(userdirectory + "\\" + username)
        if not os.path.exists(userdownloaddirectory + "\\" + username):
            os.mkdir(userdownloaddirectory + "\\" + username)
        client.send(f"Welcome {username}!".encode("utf-8"))

    return username

def handle(client, address):
    try:
        global locked_files
        #asks the client to login or signup if the client chooses login and the credentials match the client logs in 
        #otherwise the client is asked to either try again or signup. if the client chooses signup he creates an account
        client.send("1.log in\n2.sign up\n".encode("utf-8"))
        answer = client.recv(1024).decode("utf-8")
        if answer == "1":
            while True:
                flag = False
                username, password, temp_ls = help_func(client)
                for user_pass in temp_ls:
                    user, passw = user_pass.split(" ")
                    if username == user and password == passw:
                        client.send(f"Welcome {username}!".encode("utf-8"))
                        flag = True
                        break
                if flag:
                    break
                client.send("No user found! make sure the password and the username is correct\nIf you don't have an account you can sign up y/n".encode("utf-8"))
                answer2 = client.recv(1024).decode("utf-8")
                if answer2.lower() == "y":
                    username = signup(client)
                    break
        
        if answer == "2":
            username = signup(client)

#----------------------------------------------------------------------------------------------------------------#
        
        clients.append((client, username))
        follow_requests[username] = []

        client.send("type /help for the available commands.".encode("utf-8"))
        time.sleep(0.3)
        #synchronise the client's followers and following txt files in case the client logs out right after they follow another client 
        #and the other client does not accept the follow request immediately
        with open(graphpath, "r") as f:
            sync_followers = f.readlines()
            sync_followers = [x[:-1] for x in sync_followers]
        sync_following = sync_followers.copy()
        for x in range(len(sync_followers)):
            if sync_followers[x].startswith(username):
                sync_followers[x] = sync_followers[x].replace(f"{username} ", "")
                client.send(f"syncfollowers aeflq3452d {username} {sync_followers[x]}".encode("utf-8"))
                break
        time.sleep(0.3)
        temp = ""
        for x in range(len(sync_following)):
            if not sync_following[x].startswith(username) and username in sync_following[x]:
                manas = sync_following[x].split(" ")[0]
                temp += f"{manas} "
        client.send(f"syncfollowing aeflq3452d {username} {temp}".encode("utf-8"))

        while True:
            
            data = client.recv(1024).decode("utf-8")

            if data == "/help":
                msg = "\n".join(command_ls)   
                client.send(msg.encode("utf-8"))
            elif data == "/showusers": #creates a message by reading the username/password file
                with open(passpath, "r") as f:
                    ls = f.readlines()
                    ls = [x[:-1] for x in ls]
                    ls = [x.split() for x in ls]
                    ls = [x[0] for x in ls]
                    msg = "\n".join(ls)
                    client.send(msg.encode("utf-8"))
            elif data.startswith("/access_profile ") and data != "/access_profile ":
                profilename = data[16:]
                profile_flag = search_user(profilename)
                if profile_flag: #checks if the user exists
                    with open(graphpath, "r") as f:
                        ls = f.readlines()
                    ls = [x[:-1] for x in ls]
                    for x in ls:
                        if x.startswith(profilename):
                            temp_ls = x.split(" ")
                            if username in temp_ls: #checks if the user follows the other
                                photo_ls = []
                                count = 1
                                for x, y, z in os.walk(userdirectory + "\\" + profilename): #goes through all the files in the target's userdirectory saved to the server
                                    for photo in z:
                                        with open(userdirectory + "\\" + profilename + "\\" + photo, "rb") as f:
                                            all_photo = f.read()
                                        photoname = photo
                                        all_photo = str(all_photo)
                                        caption = all_photo.split("\\")
                                        caption = caption[-1][1:-1]
                                        msg = str(count) + "." + photoname + " " + caption
                                        count += 1
                                        photo_ls.append((photo, caption, profilename))
                                        client.send(msg.encode("utf-8"))
                                if len(photo_ls) == 0: #if there are no posts prints this message
                                    client.send(f"The user {profilename} has no posts yet".encode("utf-8"))
                                else: #downloads the image
                                    help_func2(client, photo_ls, username)
                            else:
                                client.send(f"You must first follow {profilename} to see their profile".encode("utf-8"))
                else:
                    client.send("User not found!".encode("utf-8"))
            elif data.startswith("/search_image ") and data != "/search_image ":
                photo_name = data[14:]
                photo_ls = []
                for x, y, z in os.walk(userdirectory): #goes through all the files in the userdirectory folder 
                    for photo in z:                    #and adds all the images with the specified name to the photo_ls list
                        if photo.lower() == photo_name.lower() or photo_name.lower().startswith(photo.lower()[:-4]):
                            with open(x + "\\" + photo, "rb") as f:
                                all_photo = f.read()
                            all_photo = str(all_photo)
                            caption = all_photo.split("\\")
                            caption = caption[-1][1:-1]
                            photo_ls.append((photo, caption, x.split("\\")[-1]))
                if len(photo_ls) == 0:
                    client.send("Image not found!".encode("utf-8"))
                else: #downloads the image
                    randphoto = random.choice(photo_ls)
                    if randphoto in locked_files:
                        client.send("The image is used by another user currently, try again later!".encode("utf-8"))
                    else:
                        client.send(f"{randphoto[0]} {randphoto[1]} from {randphoto[2]}".encode("utf-8"))
                        size = os.stat(userdirectory + "\\" + randphoto[2] + "\\" + randphoto[0]).st_size
                        lock.acquire() #file is locked
                        print(f"[{username}] locked the file {randphoto[0]} {randphoto[1]} from {randphoto[2]}")
                        locked_files.append(randphoto)
                        client.send("Do you want to download the image? y/n".encode("utf-8"))
                        answer = client.recv(1024).decode("utf-8")
                        if answer.lower() == "y":
                            client.send(f"IMAGE a453jafe2d {username} {size}".encode("utf-8")) #part of the 3-way handshake (also sends username and the size of the image)
                            with open(userdirectory + "\\" + randphoto[2] + "\\" + randphoto[0], "rb") as f:
                                image_data = f.read(int(size/10))
                                while image_data:
                                    try:
                                        client.send(image_data)
                                        client.settimeout(3)
                                        ack = client.recv(1024).decode("utf-8")
                                        image_data = f.read(int(size/10))
                                    except TimeoutError:
                                        client.send("Server did not receive ack".encode("utf-8"))
                            client.settimeout(None)
                            with open(userdirectory + "\\" + randphoto[2] + "\\" + randphoto[0], "rb") as f:
                                image = f.read()
                            with open(userdownloaddirectory + "\\" + username + "\\" + randphoto[0], "wb") as f:
                                f.write(image)
                            time.sleep(1)
                            client.send("The transmission is completed!".encode("utf-8"))
                            locked_files.remove(randphoto)
                            lock.release() #file is unlocked
                            print(f"[{username}] unlocked the file {randphoto[0]} {randphoto[1]} from {randphoto[2]}")
                        else:
                            locked_files.remove(randphoto)
                            lock.release() #file is unlocked
                            print(f"[{username}] unlocked the file {randphoto[0]} {randphoto[1]} from {randphoto[2]}")
            elif data.startswith("/follow "):
                otheruser = data[8:]
                flag = search_user(otheruser) #checks if the user exists
                if flag:
                    if username == otheruser: #checks if the user tries to follow themselves
                        client.send("You can't do that!".encode("utf-8"))
                        continue
                    flag2 = search_graph(username, otheruser) #checks if the user tries to follow someone they already follow
                    if not flag2:
                        if otheruser in follow_requests[username]: #checks if the user has already sent follow request
                            client.send("You have already sent a follow request to that user!".encode("utf-8"))
                        else: #adds the other client to their follow request and broadcasts the message to the other user
                            follow_requests[username].append(otheruser)
                            message_user = f"{username} has sent you a friend request! type /accept {username} to accept it".encode("utf-8")
                            try:
                                broadcast(otheruser, message_user)
                                client.send("Follow request sent successfully!".encode("utf-8"))
                            except:
                                client.send("Could not send follow request".encode("utf-8"))
                    else:
                        client.send(f"You already follow {otheruser}".encode("utf-8"))
                else:
                    client.send("User not found!".encode("utf-8"))
            elif data.startswith("/accept ") and data != "/accept ":
                otheruser = data[8:]
                flag = search_user(otheruser) #checks if the user exists
                flag2 = False
                if flag:
                    if otheruser == username: #checks if the user tries to accept themselves
                        client.send("You can't do that!".encode("utf-8"))
                        continue
                    if username in follow_requests[otheruser]: #makes sure that a user can't accept someone they haven't sent the user a follow request
                        follow_requests[otheruser].remove(username) #removes the otheruser from the user's follow request dict and also remove
                        if otheruser in follow_requests[username]:  #the username from the other user's follow request in case the both send a follow request to eachother
                            follow_requests[username].remove(otheruser)
                        accept_msg = "1.follow back\n2.accept follow\n3.decline follow".encode("utf-8")
                        client.send(accept_msg)
                        while True:
                            num = client.recv(1024).decode("utf-8")
                            if num.isnumeric():
                                if int(num) >= 1 and int(num) <= 3:
                                    break
                                else:
                                    client.send("Invalid number!".encode("utf-8"))
                            else:
                                client.send("That is not a number!".encode("utf-8"))
                        if num == "1": #follow back if the user already follows the other then the user just accepts the follow request
                            accept_follow(client, username, otheruser)
                            flag3 = search_graph(username, otheruser)
                            if not flag3:
                                follow_requests[username].append(otheruser)
                                message_user = f"{username} has sent you a friend request! type /accept {username} to accept it".encode("utf-8")
                                try:
                                    broadcast(otheruser, message_user)
                                    client.send("Follow request sent successfully!".encode("utf-8"))
                                except:
                                    client.send("Could not send follow request".encode("utf-8"))
                        elif num == "2": #accept follow
                            accept_follow(client, username, otheruser)
                        else: #decline follow
                            client.send("Follow request declined!".encode("utf-8"))
                            broadcast(otheruser, f"{username} has declined your follow request!".encode("utf-8"))
                    else:
                        client.send(f"{otheruser} hasn't sent you a follow request".encode("utf-8"))
                else:
                    client.send("User not found!".encode("utf-8"))
            elif data.startswith("/unfollow ") and data != "/unfollow ":
                otheruser = data[10:]
                flag = search_user(otheruser) #checks if the user exists
                if flag:
                    if username == otheruser: #checks if the user tries to unfollow themselves
                        client.send("You can't do that!".encode("utf-8"))
                        continue
                    flag2 = search_graph(username, otheruser) #checks if the user already doen't follow the other user
                    if flag2: #removes the user's name from the social grapgh of the other user and signals the
                        client.send(f"unfollowinit {username} {otheruser}".encode("utf-8")) #two users to remove the user's name from their followers/following files
                        broadcast(otheruser, f"removefromfollowers {otheruser} {username}".encode("utf-8"))
                        with open(graphpath, "r") as f:
                            ls = f.readlines()
                        for x in range(len(ls)):
                            if ls[x].startswith(otheruser):
                                ls[x] = ls[x].replace(f" {username}", "")
                        with open(graphpath, "w") as f:
                            f.writelines(ls)
                        client.send(f"Unfollowed {otheruser} successfully!".encode("utf-8"))
                    else:
                        client.send(f"You already don't follow {otheruser}".encode("utf-8"))
                else:
                    client.send("User not found!".encode("utf-8"))
                pass
            elif data == "/showfollowing":
                client.send(f"showfollowing {username}".encode("utf-8"))
            elif data == "/showfollowers":
                client.send(f"showfollowers {username}".encode("utf-8"))
            elif data == "/upload":
                try: #sends a message so the client knows its time to send an image to the server
                    client.send(f"sdj42sdfg3 Choose an image to upload {username}".encode("utf-8"))
                    imagepath = client.recv(1024).decode("utf-8")
                    if imagepath.startswith("STOP jk6gtj4isw"): #if the client doen't choose anything it just stops the upload
                        continue
                    with open(userdirectory + "\\" + username + "\\" + imagepath.split("\\")[-1], "wb+") as f:
                        image_chunk = client.recv(2048)
                        while image_chunk:
                            f.write(image_chunk)
                            client.settimeout(1)
                            image_chunk = client.recv(2048)
                except TimeoutError:
                    client.settimeout(None)
                    with open(graphpath, "r") as f:
                        followers = f.readlines()
                        followers = [x[:-1] for x in followers]
                    for x in range(len(followers)):
                        if followers[x].startswith(username):
                            followerstosend = followers[x].split(" ")[1:-1]
                    for follower in followerstosend:
                        broadcast(follower, f"{username} has creadted a new post!".encode("utf-8"))
                    continue
    except Exception:
        locked_files = []
        try:
            clients.remove((client, username))
        except:
            pass
        client.close()

def run():

    print("Server opened!")

    while True:

        client, address = server.accept()

        print(f"connection from ({address})")

        t1 = threading.Thread(target=handle, args=(client, address))
        t1.start()

run()