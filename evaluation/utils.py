import torch
import torch.distributed as dist

#from SwissArmyTransformer import mpu, get_tokenizer


def print_rank_0(*args, **kwargs):
    # if torch.distributed.get_rank() == 0:
    print(*args, **kwargs)


def build_data_loader(dataset, micro_batch_size, num_workers, drop_last, collate_fn=None):
    # Sampler.
    '''
    world_size = mpu.get_data_parallel_world_size()
    rank = mpu.get_data_parallel_rank()
    sampler = torch.utils.data.distributed.DistributedSampler(
        dataset, num_replicas=world_size, rank=rank, shuffle=False
    )
    '''

    # Data loader. Note that batch size is the per GPU batch size.
    data_loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=micro_batch_size,
        shuffle=False,
        num_workers=num_workers,
        drop_last=drop_last,
        pin_memory=True,
        collate_fn=collate_fn,
    )

    return data_loader

'''
def gather_result(prediction, total_length, micro_batch_size):
    """
    @param prediction: Local predictions with order defined by distributed sampler
    @param total_length: Total sample num
    @return: [sample_0, sample_1, ..., sample_{total_length-1}]
    """
    torch.cuda.empty_cache()
    world_size = mpu.get_data_parallel_world_size()
    prediction_gathered = [None for _ in range(world_size)]
    dist.all_gather_object(prediction_gathered, prediction, group=mpu.get_data_parallel_group())
    prediction = []
    for i in range(len(prediction_gathered[0])):
        for j in range(micro_batch_size):
            for k in range(world_size):
                if j < len(prediction_gathered[k][i]):
                    prediction.append(prediction_gathered[k][i][j])
    prediction = prediction[:total_length]
    return prediction
'''

def get_tokenized_input(item, key):
    if key in item:
        return item[key]
    tokenizer = get_tokenizer()
    pretokenized_key = key + "_pretokenized"
    assert pretokenized_key in item
    if isinstance(item[pretokenized_key], list):
        result = []
        for raw in item[pretokenized_key]:
            result.append(tokenizer.tokenize(raw))
        return result
    else:
        return tokenizer.tokenize(item[pretokenized_key])

"""
Server Side Events (SSE) client for Python.
Provides a generator of SSE received through an existing HTTP response.
"""
import json
# Copyright (C) 2016-2017 SignalFx, Inc. All rights reserved.

import logging
import random

import requests
import pprint

__author__ = "Maxime Petazzoni <maxime.petazzoni@bulix.org>"
__email__ = "maxime.petazzoni@bulix.org"
__copyright__ = "Copyright (C) 2016-2017 SignalFx, Inc. All rights reserved."
__all__ = ["SSEClient"]

_FIELD_SEPARATOR = ":"

class SSEClient(object):
    """Implementation of a SSE client.
    See http://www.w3.org/TR/2009/WD-eventsource-20091029/ for the
    specification.
    """

    def __init__(self, event_source, char_enc="utf-8"):
        """Initialize the SSE client over an existing, ready to consume
        event source.
        The event source is expected to be a binary stream and have a close()
        method. That would usually be something that implements
        io.BinaryIOBase, like an httplib or urllib3 HTTPResponse object.
        """
        self._logger = logging.getLogger(self.__class__.__module__)
        self._logger.debug("Initialized SSE client from event source %s", event_source)
        self._event_source = event_source
        self._char_enc = char_enc

    def _read(self):
        """Read the incoming event source stream and yield event chunks.
        Unfortunately it is possible for some servers to decide to break an
        event into multiple HTTP chunks in the response. It is thus necessary
        to correctly stitch together consecutive response chunks and find the
        SSE delimiter (empty new line) to yield full, correct event chunks."""
        data = b""
        for chunk in self._event_source:
            for line in chunk.splitlines(True):
                data += line
                if data.endswith((b"\r\r", b"\n\n", b"\r\n\r\n")):
                    yield data
                    data = b""
        if data:
            yield data

    def events(self):
        for chunk in self._read():
            event = Event()
            # Split before decoding so splitlines() only uses \r and \n
            for line in chunk.splitlines():
                # Decode the line.
                line = line.decode(self._char_enc)

                # Lines starting with a separator are comments and are to be
                # ignored.
                if not line.strip() or line.startswith(_FIELD_SEPARATOR):
                    continue

                data = line.split(_FIELD_SEPARATOR, 1)
                field = data[0]

                # Ignore unknown fields.
                if field not in event.__dict__:
                    self._logger.debug("Saw invalid field %s while parsing " "Server Side Event", field)
                    continue

                if len(data) > 1:
                    # From the spec:
                    # "If value starts with a single U+0020 SPACE character,
                    # remove it from value."
                    if data[1].startswith(" "):
                        value = data[1][1:]
                    else:
                        value = data[1]
                else:
                    # If no value is present after the separator,
                    # assume an empty value.
                    value = ""

                # The data field may come over multiple lines and their values
                # are concatenated with each other.
                if field == "data":
                    event.__dict__[field] += value + "\n"
                else:
                    event.__dict__[field] = value

            # Events with no data are not dispatched.
            if not event.data:
                continue

            # If the data field ends with a newline, remove it.
            if event.data.endswith("\n"):
                event.data = event.data[0:-1]

            # Empty event names default to 'message'
            event.event = event.event or "message"

            # Dispatch the event
            self._logger.debug("Dispatching %s...", event)
            yield event

    def close(self):
        """Manually close the event source stream."""
        self._event_source.close()


class Event(object):
    """Representation of an event from the event stream."""

    def __init__(self, id=None, event="message", data="", retry=None):
        self.id = id
        self.event = event
        self.data = data
        self.retry = retry

    def __str__(self):
        s = "{0} event".format(self.event)
        if self.id:
            s += " #{0}".format(self.id)
        if self.data:
            s += ", {0} byte{1}".format(len(self.data), "s" if len(self.data) else "")
        else:
            s += ", no data"
        if self.retry:
            s += ", retry in {0}ms".format(self.retry)
        return