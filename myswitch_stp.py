from switchyard.lib.userlib import *
from spanningtreemessage import SpanningTreeMessage
from _thread import start_new_thread
import threading
import time

def main(net):
	my_interfaces = net.interfaces() 
	mymacs = [intf.ethaddr for intf in my_interfaces]
	fwd_table = []
	fwd_mode = {}

	for intf in my_interfaces:
		fwd_mode[intf.name] = 1
		log_info(intf.name)
	

	#stp packet id
	id = min(mymacs)
	hops = 0
	root_port = ""

	def mk_stp_pkt(root_id, hops, hwsrc="20:00:00:00:00:01", hwdst="ff:ff:ff:ff:ff:ff"):
		spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
		Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
		pkt = Ethernet(src=hwsrc,
							dst=hwdst,
							ethertype=EtherType.SLOW) + spm
		xbytes = pkt.to_bytes()
		p = Packet(raw=xbytes)
		return p

	pkt = mk_stp_pkt('20:00:00:00:00:01', 0);
 
	def send_stp(pkt):
		while id == min(mymacs):
			for intf in my_interfaces:
				log_debug ("Flooding packet {} to {}".format(pkt, intf.name))
				net.send_packet(intf.name, pkt)
			time.sleep(2)

	
	threading.Thread(group=None, target=send_stp, name=None, args=(pkt,)).start()
	
	while True:
		log_info("LISTENING FOR PACKET\n")
		try:
			timestamp,input_port,packet = net.recv_packet()
		except NoPackets:
			continue
		except Shutdown:
			return

		log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

		if packet.has_header(SpanningTreeMessage):
			stp_in = packet[SpanningTreeMessage]
			if stp_in.root < id or (stp_in.root == id and stp_in.hops_to_root + 1 < hops):
				id = stp_in.root
				root_port = input_port
				hops = stp_in.hops_to_root + 1

				new_pkt = mk_stp_pkt(id, hops)

				for intf in my_interfaces:
					if input_port != intf.name:
						log_debug ("Flooding packet {} to {}".format(new_pkt, intf.name))
						net.send_packet(intf.name, new_pkt)
				fwd_mode[input_port] = 1
			
			elif stp_in.root == id and stp_in.hops_to_root + 1 == hops and input_port != root_port:
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
							for mode in fwd_mode:
								log_info(mode + " " + str(fwd_mode[mode]))
							if input_port != intf.name and fwd_mode[intf.name] == 1:
								log_debug ("Flooding packet {} to {}".format(packet, intf.name))
								net.send_packet(intf.name, packet)

	net.shutdown()
