from switchyard.lib.userlib import *

Class FWDTableNode:
        def __init__(self, mac = None, port = None):
            self.mac = None
            self.port = None
            self.nextNode = None
            self.prevNode = None


def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    head = FWDTableNode()
    tail = head
    tbl_size = 0

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

        next = head.next
        while next is not None:
            if next.nextNode.mac == packet.ethaddr:
                next.prevNode.nextNode = next.nextNode
                next.nextNode.prevNode = next.prevNode
                tbl_size -= 1
                break
            next = next.nextNode

        new_front = FWDTableNode(mac = packet[Ethernet].src, port = input_port)
        new_front.nextNode = head.nextNode
        new_front.prevNode = head
        head.nextNode = new_front

        if tbl_size == 5:
            tail.prevNode.NextNode = None
        else:
            tbl_size += 1    
            


    

        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        else:
            next = head.nextNode
            send_port = None
            while next is not None:
                if next.nextNode.mac == packet.ethaddr:
                    send_port = next.port
                    next.prevNode.nextNode = next.nextNode
                    next.nextNode.prevNode = next.prevNode

                    new_front.nextNode = head.nextNode
                    new_front.prevNode = head
                    head.nextNode = new_front
                    break

            if send_port is not None:
                net.send_packet(send_port, packet)   
            else:
                for intf in my_interfaces:
                    if input_port != intf.name:
                        log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                        net.send_packet(intf.name, packet)
    net.shutdown()