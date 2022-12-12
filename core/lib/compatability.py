"""
module rpm packaging changes:

lxml: python-lxml changed to python3-lxml
"""
import subprocess
import base64
import io
import hashlib

# module renaming and/or refactoring:

# __builtin__ changed to builtins
try:
    import __builtin__ as builtin
except ImportError:
    import builtins as builtin
# StringIO: changed to io
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# urlparse changed to urllib.parse
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse

# xmlrpclib split into xmlrpc.client and xmlrpc.server
try:
    from xmlrpclib import Binary as XmlrpcBinary
except ImportError:
    from xmlrpc.client import Binary as XmlrpcBinary

try:
    from xmlrpclib import Fault as XmlrpcFault
except ImportError:
    from xmlrpc.client import Fault as XmlrpcFault

try:
    from xmlrpclib import ProtocolError as XmlrpcProtocolError
except ImportError:
    from xmlrpc.client import ProtocolError as XmlrpcProtocolError

try:
    from xmlrpclib import ServerProxy as XmlrpcServerProxy
except ImportError:
    from xmlrpc.client import ServerProxy as XmlrpcServerProxy

try:
    from xmlrpclib import Transport as XmlrpcTransport
except ImportError:
    from xmlrpc.client import Transport as XmlrpcTransport

# urllib2 split to urllib.request and urllib.error
try:
    from urllib2 import build_opener as urllib_build_opener
    from urllib2 import ProxyHandler as UrllibProxyHandler
    from urllib2 import Request as UrllibRequest
    from urllib2 import urlopen as urllib_urlopen
    from urllib2 import HTTPError as Urllib_HTTPError
except ImportError:
    from urllib.request import build_opener as urllib_build_opener
    from urllib.request import ProxyHandler as UrllibProxyHandler
    from urllib.request import Request as UrllibRequest
    from urllib.request import urlopen as urllib_urlopen
    from urllib.request import HTTPError as Urllib_HTTPError

# unicode() is str() in python3
def rhcert_unicode(s):
    try:
        return unicode(s)
    except NameError:
        pass
    return str(s)


def rhcert_is_string_or_unicode(value):
    try:
        return (isinstance(value, unicode) or isinstance(value, str))
    except NameError:
        return (isinstance(value, str))


def rhcert_string_or_unicode(value):
    if rhcert_is_string_or_unicode(value):
        return value
    return ""


def rhcert_get_status_output(commandString):
    try:  # python2 - stick with commands.getstatusoutput for now
        import commands
        return commands.getstatusoutput(commandString)
    except ImportError:  # python3 - should also work for python2
        pass
    return subprocess.getoutput(commandString)

def rhcert_make_unicode(value):
    """ try to make a unicode value """
    # python3 has no 'unicode' type - str is unicode already
    try:
        unicodeType = unicode
    except NameError:
        unicodeType = str

    if not value:
        return u""
    # this is the same for python2 and python3, so just use decode("utf-8")
    if type(value) is bytes:
        return value.decode("utf-8")

    if type(value) is unicodeType:
        return value
    try:  # int, float, etc?
        return unicodeType(value)
    except:
        pass

    try:  # works for xmlrpc.Binary
        if str != unicodeType:
            return unicodeType(value.data, "utf-8")
        else:
            return str(value.data)
    except:
        pass
    # Failed to convert
    return u""


def rhcert_make_str(value):
    try:
        if type(value) is unicode:
            return value.encode('utf-8', 'ignore')
        elif isinstance(value, list):
            return [rhcert_make_str(x) for x in value]
    except NameError: # python3
        if type(value) is bytes:
            return value.decode('utf-8')
    return str(value)


def rhcert_base64_encode(data):
    """ encode data (either str or bytes) base64
        result type is bytes
    """
    try:  # python3
        if not isinstance(data, bytes):
            data = bytes(data, encoding='utf-8')
        return base64.b64encode(data)
    except TypeError:  # python2
        return data.encode('base64')

def rhcert_base64_decode(base64data):
    """ decode data (either str or bytes) base64
        result type is bytes
    """
    try:  # python3
        if not isinstance(base64data, bytes):
            base64data = bytes(base64data, encoding='utf-8')
        return base64.b64decode(base64data)
    except TypeError:  # python2
        return str(base64data).decode("base64")


def rhcert_base64_encode_and_md5(filePath):
    """ encode a file contents base64 with md5 checksum """
    encodeFile = io.open(filePath, 'rb')
    data = encodeFile.read()
    encodeFile.close()

    try:  # python2
        dataBytes = data.encode('utf-8', 'ignore') if type(data) is unicode else data
        md5 = hashlib.md5(dataBytes).hexdigest()
        data64 = base64.b64encode(dataBytes)
    except NameError:  # python3
        dataBytes = data if isinstance(data, bytes) else bytes(data, encoding='utf-8')
        md5 = hashlib.md5(dataBytes).hexdigest()
        data64 = base64.b64encode(dataBytes).decode("utf-8")

    return (data64, md5)
