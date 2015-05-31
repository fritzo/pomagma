# Copyright (c) 2014, Salesforce.com, Inc.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# - Neither the name of Salesforce.com nor the names of its contributors
#   may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import bz2
import gzip
import os
import struct
from google.protobuf.descriptor import FieldDescriptor


def mkdir_p(dirname):
    'like mkdir -p'
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except OSError as e:
            if not os.path.exists(dirname):
                raise e


def open_compressed(filename, mode='r'):
    if 'w' in mode:
        dirname = os.path.dirname(filename)
        if dirname:
            mkdir_p(dirname)
    if filename.endswith('.bz2'):
        return bz2.BZ2File(filename, mode.replace('b', ''))
    elif filename.endswith('.gz'):
        return gzip.GzipFile(filename, mode)
    else:
        return file(filename, mode)


def protobuf_stream_write(item, fd):
    assert isinstance(item, str), item
    fd.write(struct.pack('<I', len(item)))
    fd.write(item)


def protobuf_stream_read(fd):
    size_str = fd.read(4)
    if len(size_str) < 4:
        raise StopIteration
    size = struct.unpack('<I', size_str)[0]
    return fd.read(size)


def protobuf_stream_dump(stream, filename):
    with open_compressed(filename, 'wb') as f:
        for item in stream:
            protobuf_stream_write(item, f)


class protobuf_stream_load(object):
    def __init__(self, filename):
        self.fd = open_compressed(filename, 'rb')

    def __iter__(self):
        return self

    def next(self):
        return protobuf_stream_read(self.fd)

    def close(self):
        self.fd.close()


def protobuf_to_dict(message):
    assert message.IsInitialized()
    raw = {}
    for field in message.DESCRIPTOR.fields:
        value = getattr(message, field.name)
        if field.label == FieldDescriptor.LABEL_REPEATED:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                value = map(protobuf_to_dict, value)
            else:
                value = list(value)
            if len(value) == 0:
                value = None
        else:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                if value.IsInitialized():
                    value = protobuf_to_dict(value)
                else:
                    value = None
        if value is not None:
            raw[field.name] = value
    return raw


def dict_to_protobuf(raw, message):
    assert isinstance(raw, dict)
    for key, raw_value in raw.iteritems():
        if isinstance(raw_value, dict):
            value = getattr(message, key)
            dict_to_protobuf(raw_value, value)
        elif isinstance(raw_value, list):
            value = getattr(message, key)
            list_to_protobuf(raw_value, value)
        else:
            setattr(message, key, raw_value)


def list_to_protobuf(raw, message):
    assert isinstance(raw, list)
    if raw:
        if isinstance(raw[0], dict):
            for value in raw:
                dict_to_protobuf(value, message.add())
        elif isinstance(raw[0], list):
            for value in raw:
                list_to_protobuf(value, message.add())
        else:
            message[:] = raw
