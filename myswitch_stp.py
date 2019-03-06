from switchyard.lib.userlib import *
from spanningtreemessage import SpanningTreeMessage
from _thread import start_new_thread
import threading
import time

def main(net):
	my_interfaces = net.interfaces() 
	mymacs = [intf.ethaddr for intf in my_interfaces]
	fwd_mode = {}

	for mac in mymacs:
		fwd_mode[mac] = 1

	#stp packet id
	id = min(mymacs)
	hops = 0
	root_port = ""

	spm = SpanningTreeMessage(id, hops_to_root=0)

	Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)

	pkt = Ethernet(src= id, 
       				dst= "ff:ff:ff:ff:ff:ff",
   	      		ethertype=EtherType.SLOW) + spm
 
	def send_stp(pkt):
		while id == min(mymacs):
			for intf in my_interfaces:
				log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
				net.send_packet(intf.name, pkt)
			time.sleep(2)

	
	threading.Thread(group=None, target=send_stp, name=None, args=(pkt,)).start()
	
	while True:
		try:
			timestamp,input_port,packet = net.recv_packet()
		except NoPackets:
			continue
		except Shutdown:
			return

		log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

		if packet.has_header(SpanningTreeMessage):
			stp_in = packet.get_header(hdrclass)
			if stp_in.root() < id or (stp_in.root() == id and stp_in.hops_to_root() + 1 < hops):
				id = stp_in.root()
				root_port = input_port
				hops = stp_in.hops_to_root() + 1
				stp_in.hops_to_root(hops)

				for intf in my_interfaces:
					if input_port != intf.name:
						log_debug ("Flooding packet {} to {}".format(packet, intf.name))
						net.send_packet(intf.name, packet)
				fwd_mode[input_port] = 1
			
			elif stp_in.root() == id and stp_in.hops_to_root() + 1 == hops and input_port != root_port:
				fwd_mode[input_port] = 0				

		else:	
			for i in range(len(fwd_table)):
				if fwd_table[i][0] == packet[Ethernet].src:
					fwd_table.pop(i)
					break
		
			fwd_table.insert(0, (packet[Ethernet].src, input_port));

			if len(fwd_table) == 5:
				fwd_table.pop(4);			           

			if packet[0].dst in mymacs:
				log_debug ("Packet intended for me")
			else:					
					send_port = None
					for i in range(len(fwd_table)):
						if fwd_table[i][0] == packet[Ethernet].dst:
							mru_entry = fwd_table.pop(i)
							send_port = mru_entry[1]
							fwd_table.insert(0, mru_entry)
							break
					if send_port is not None:
						net.send_packet(send_port, packet)   
					else:
						for intf in my_interfaces:
							if input_port != intf.name and fwd_mode[input_port] == 1:
								log_debug ("Flooding packet {} to {}".format(packet, intf.name))
								net.send_packet(intf.name, packet)

	net.shutdown()
