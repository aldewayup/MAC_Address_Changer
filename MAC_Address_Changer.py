import subprocess
import regex as re
import string
import random

#networkifpath is path in the registry where n/w i/f located
networkifpath =  r"HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e972-e325-11ce-bfc1-08002be10318}"

#transportname is regex to extract transport name looks like {AF1B45DB-B5D4-46D0-B4EA-3E18FA49BF5F}
transportregex = re.compile("{.+}")

#macregex is regex to extract mac address
macregex = re.compile(r"([A-Z0-9]{2}[:-]){5}([A-Z0-9]{2})")

def get_random_mac_addr():
    """generate and return random mac addr in windows format"""
    #get hexdigits uppercased
    uppercase_hexdigits = ''.join(set(string.hexdigits.upper()))
    #2nd char must 2, 4, A, or E
    return random.choice(uppercase_hexdigits) + random.choice("24AE") + "".join(random.sample(uppercase_hexdigits, k=10))

def clean_mac(mac):
    """remove '-' and ':' from mac addr while uppercasing"""
    return "".join(c for c in mac if c in string.hexdigits).upper()

def get_connected_adapters_mac_addr():
    """list to collect connected adapters MAC addr along with transport name"""
    connected_adapters_mac = []
    #use getmac command to extract
    for potential_mac in subprocess.check_output('getmac').decode().splitlines():
        #parse the MAC addr 
        mac_addr = macregex.search(potential_mac)
        #parse transport name
        transport_name = transportregex.search(potential_mac)
        if mac_addr and transport_name:
            connected_adapters_mac.append((mac_addr.group(), transport_name.group()))

    return connected_adapters_mac

#user chooses appropriate adapter
def get_user_adapter_choice(connected_adapters_mac):
    """print the available adapters"""
    for i, option in enumerate(connected_adapters_mac):
        print(f"{i}: {option[0]},{option[1]}")
    if len(connected_adapters_mac) <= 1:
        #choose immed if only one adapter exists
        return connected_adapters_mac[0]
    #prompt user to choose a network adapter index
    try:
        choice = int(input("Please choose i/f you want to change MAC addr of: "))
        #return target chosen MAC and transport name from reg query command
        return connected_adapters_mac[choice]
    except:
        #if -for whatever reason an error is raised, quit
        print("Not a valid choice. \n Aborting ...")
        exit()

def change_mac_addr(adapter_transport_name, new_mac_addr):
    """use reg query to get available adapters from the registry"""
    output = subprocess.check_output(f"reg QUERY " + networkifpath.replace("\\\\","\\")).decode()
    for interface in re.findall(rf"{networkifpath}\\\d+",output):
        #get the adapter index
        adapter_index = int(interface.split("\\")[-1])
        interface_content = subprocess.check_output(f"reg QUERY {interface.strip()}").decode()
        #compare the current adapter's content against
        if adapter_transport_name in interface_content:
            #if transport name of adapter found on output of reg QUERY we ve found the adapter. 
            #Change the MAC addr using reg ADD command
            new_mac_addr_formatted = "".join(["{:02X}".format(int(i, 16)) for i in new_mac_addr.split(":")])
            changing_mac_output = subprocess.check_output(f"reg add {interface} /v NetworkAddr /t REG_SZ /d {new_mac_addr_formatted} /f").decode()
            print(changing_mac_output)
            break

    return adapter_index


def disable_adapter(adapter_index):
    #use wmic command to disable in order to reflect changed  MAC address

    disable_output = subprocess.check_output(f"wmic path win32_networkadapter where index={adapter_index} call disable").decode()
    return disable_output

def enable_adapter(adapter_index):
    #use wmic command to enable in order to reflect changed  MAC address

    enable_output = subprocess.check_output(f"wmic path win32_networkadapter where index={adapter_index} call enable").decode()
    return enable_output

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Python Windows MAC Changer")
    parser.add_argument("-r", "--random", action="store_true", help="Whether to generate a random MAC addr")
    parser.add_argument("-m","--mac",help="The new MAC you wnat to change to")
    args = parser.parse_args()

    if args.random:
        #if random parameter is set, generate a random MAC
        new_mac_addr = get_random_mac_addr()
    elif args.mac:
        #if mac is set, use it after cleaning
        new_mac_addr = clean_mac(args.mac)

    connected_adapters = get_connected_adapters_mac_addr()
    old_addr, target_transport = get_user_adapter_choice(connected_adapters)
    print("[*] Old MAC addr:", old_addr)
    adapter_index =  change_mac_addr(target_transport,new_mac_addr)
    print("[+] Changed to:", new_mac_addr)
    disable_adapter(adapter_index)
    print("[-] Adapter disabled")
    enable_adapter(adapter_index)
    print("[+] Adapter enabled")