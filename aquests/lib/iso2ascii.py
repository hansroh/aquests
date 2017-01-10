import re

iso2ascii = {
		chr(161):'A', chr(163):'L', chr(165):'L', chr(166):'S', chr(169):'S',
		chr(170):'S', chr(171):'T', chr(172):'Z', chr(174):'Z', chr(175):'Z',
		chr(177):'a', chr(179):'l', chr(181):'l', chr(182):'s', chr(185):'s',
		chr(186):'s', chr(187):'t', chr(188):'z', chr(190):'z', chr(191):'z',
		chr(192):'R', chr(193):'A', chr(194):'A', chr(195):'A', chr(196):'A',
		chr(197):'L', chr(198):'C', chr(199):'C', chr(200):'C', chr(201):'E',
		chr(202):'E', chr(203):'E', chr(204):'E', chr(205):'I', chr(206):'I',
		chr(207):'D', chr(208):'D', chr(209):'N', chr(210):'N', chr(211):'O',
		chr(212):'O', chr(213):'O', chr(214):'O', chr(216):'R', chr(217):'U',
		chr(218):'U', chr(219):'U', chr(220):'U', chr(221):'Y', chr(222):'T',
		chr(223):'s', chr(224):'r', chr(225):'a', chr(226):'a', chr(227):'a',
		chr(228):'a', chr(229):'l', chr(230):'c', chr(231):'c', chr(232):'c',
		chr(233):'e', chr(234):'e', chr(235):'e', chr(236):'e', chr(237):'i',
		chr(238):'i', chr(239):'d', chr(240):'d', chr(241):'n', chr(242):'n',
		chr(243):'o', chr(244):'o', chr(245):'o', chr(246):'o', chr(248):'r',
		chr(249):'u', chr(250):'u', chr(251):'u', chr(252):'u', chr(253):'y',
		chr(254):'t'
	}


rx_non_ascii = re.compile ("[^\x01-\x80]")
def decode (k):	
	if rx_non_ascii.search (k):
		for u, a in list(iso2ascii.items ()):
			k = k.replace (u, a)	
	return k
	
	
	
if __name__ == "__main__":	
	print(decode ("Norra Agatan 10"))
