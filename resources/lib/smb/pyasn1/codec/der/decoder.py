# DER decoder
from resources.lib.smb.pyasn1.type import univ
from resources.lib.smb.pyasn1.codec.cer import decoder

decode = decoder.Decoder(decoder.tagMap, decoder.typeMap)
