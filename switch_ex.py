from switchyard.lib.userlib import *

def main(net):
	my_interfaces = net.interfaces() 
	mymacs = [intf.ethaddr for intf in my_interfaces]
	fwd_table = []
	

	while True:
		try:
			timestamp,input_port,packet = net.recv_packet()
		except NoPackets:
			continue
		except Shutdown:
			return

		log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))

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
						if input_port != intf.name:
							log_debug ("Flooding packet {} to {}".format(packet, intf.name))
							net.send_packet(intf.name, packet)

	net.shutdown()
