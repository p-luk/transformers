{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# coding=utf-8\n",
    "# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.\n",
    "# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.\n",
    "#\n",
    "# Licensed under the Apache License, Version 2.0 (the \"License\");\n",
    "# you may not use this file except in compliance with the License.\n",
    "# You may obtain a copy of the License at\n",
    "#\n",
    "#     http://www.apache.org/licenses/LICENSE-2.0\n",
    "#\n",
    "# Unless required by applicable law or agreed to in writing, software\n",
    "# distributed under the License is distributed on an \"AS IS\" BASIS,\n",
    "# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n",
    "# See the License for the specific language governing permissions and\n",
    "# limitations under the License.\n",
    "\"\"\" GLUE processors and helpers \"\"\"\n",
    "\n",
    "import logging\n",
    "import os\n",
    "import json\n",
    "import sys\n",
    "import csv\n",
    "from ...file_utils import is_tf_available\n",
    "from .utils import DataProcessor, InputExample, InputFeatures\n",
    "\n",
    "\n",
    "if is_tf_available():\n",
    "    import tensorflow as tf\n",
    "\n",
    "logger = logging.getLogger(__name__)\n",
    "\n",
    "\n",
    "def glue_convert_examples_to_features(\n",
    "    examples,\n",
    "    tokenizer,\n",
    "    max_length=512,\n",
    "    task=None,\n",
    "    label_list=None,\n",
    "    output_mode=None,\n",
    "    pad_on_left=False,\n",
    "    pad_token=0,\n",
    "    pad_token_segment_id=0,\n",
    "    mask_padding_with_zero=True,\n",
    "):\n",
    "    \"\"\"\n",
    "    Loads a data file into a list of ``InputFeatures``\n",
    "\n",
    "    Args:\n",
    "    examples: List of ``InputExamples`` or ``tf.data.Dataset`` containing the examples.\n",
    "    tokenizer: Instance of a tokenizer that will tokenize the examples\n",
    "    max_length: Maximum example length\n",
    "    task: GLUE task\n",
    "    label_list: List of labels. Can be obtained from the processor using the ``processor.get_labels()`` method\n",
    "    output_mode: String indicating the output mode. Either ``regression`` or ``classification``\n",
    "    pad_on_left: If set to ``True``, the examples will be padded on the left rather than on the right (default)\n",
    "    pad_token: Padding token\n",
    "    pad_token_segment_id: The segment ID for the padding token (It is usually 0, but can vary such as for XLNet where it is 4)\n",
    "    mask_padding_with_zero: If set to ``True``, the attention mask will be filled by ``1`` for actual values\n",
    "        and by ``0`` for padded values. If set to ``False``, inverts it (``1`` for padded values, ``0`` for\n",
    "        actual values)\n",
    "\n",
    "    Returns:\n",
    "    If the ``examples`` input is a ``tf.data.Dataset``, will return a ``tf.data.Dataset``\n",
    "    containing the task-specific features. If the input is a list of ``InputExamples``, will return\n",
    "    a list of task-specific ``InputFeatures`` which can be fed to the model.\n",
    "\n",
    "    \"\"\"\n",
    "    is_tf_dataset = False\n",
    "    if is_tf_available() and isinstance(examples, tf.data.Dataset):\n",
    "        is_tf_dataset = True\n",
    "\n",
    "    if task is not None:\n",
    "        processor = glue_processors[task]()\n",
    "        if label_list is None:\n",
    "            label_list = processor.get_labels()\n",
    "            logger.info(\"Using label list %s for task %s\" % (label_list, task))\n",
    "        if output_mode is None:\n",
    "            output_mode = glue_output_modes[task]\n",
    "            logger.info(\"Using output mode %s for task %s\" % (output_mode, task))\n",
    "\n",
    "    label_map = {label: i for i, label in enumerate(label_list)}\n",
    "\n",
    "    features = []\n",
    "    for (ex_index, example) in enumerate(examples):\n",
    "        len_examples = 0\n",
    "        if is_tf_dataset:\n",
    "            example = processor.get_example_from_tensor_dict(example)\n",
    "            example = processor.tfds_map(example)\n",
    "            len_examples = tf.data.experimental.cardinality(examples)\n",
    "        else:\n",
    "            len_examples = len(examples)\n",
    "        if ex_index % 10000 == 0:\n",
    "            logger.info(\"Writing example %d/%d\" % (ex_index, len_examples))\n",
    "\n",
    "        inputs = tokenizer.encode_plus(example.text_a, example.text_b, add_special_tokens=True, return_token_type_ids=True, max_length=max_length,)\n",
    "        input_ids, token_type_ids = inputs[\"input_ids\"], inputs[\"token_type_ids\"]\n",
    "\n",
    "    # The mask has 1 for real tokens and 0 for padding tokens. Only real\n",
    "    # tokens are attended to.\n",
    "        attention_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)\n",
    "\n",
    "    # Zero-pad up to the sequence length.\n",
    "        padding_length = max_length - len(input_ids)\n",
    "        if pad_on_left:\n",
    "            input_ids = ([pad_token] * padding_length) + input_ids\n",
    "            attention_mask = ([0 if mask_padding_with_zero else 1] * padding_length) + attention_mask\n",
    "            token_type_ids = ([pad_token_segment_id] * padding_length) + token_type_ids\n",
    "        else:\n",
    "            input_ids = input_ids + ([pad_token] * padding_length)\n",
    "            attention_mask = attention_mask + ([0 if mask_padding_with_zero else 1] * padding_length)\n",
    "            token_type_ids = token_type_ids + ([pad_token_segment_id] * padding_length)\n",
    "\n",
    "        assert len(input_ids) == max_length, \"Error with input length {} vs {}\".format(len(input_ids), max_length)\n",
    "        assert len(attention_mask) == max_length, \"Error with input length {} vs {}\".format(\n",
    "            len(attention_mask), max_length\n",
    "    \t)\n",
    "        assert len(token_type_ids) == max_length, \"Error with input length {} vs {}\".format(\n",
    "            len(token_type_ids), max_length\n",
    "\t)\n",
    "\n",
    "        if output_mode == \"classification\":\n",
    "            label = label_map[example.label]\n",
    "        elif output_mode == \"regression\":\n",
    "            label = float(example.label)\n",
    "        else:\n",
    "            raise KeyError(output_mode)\n",
    "\n",
    "        if ex_index < 5:\n",
    "            logger.info(\"*** Example ***\")\n",
    "            logger.info(\"guid: %s\" % (example.guid))\n",
    "            logger.info(\"input_ids: %s\" % \" \".join([str(x) for x in input_ids]))\n",
    "            logger.info(\"attention_mask: %s\" % \" \".join([str(x) for x in attention_mask]))\n",
    "            logger.info(\"token_type_ids: %s\" % \" \".join([str(x) for x in token_type_ids]))\n",
    "            logger.info(\"label: %s (id = %d)\" % (example.label, label))\n",
    "\n",
    "        features.append(\n",
    "            InputFeatures(\n",
    "                input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids, label=label\n",
    "        \t)\n",
    "    \t)\n",
    "\n",
    "    if is_tf_available() and is_tf_dataset:\n",
    "\n",
    "        def gen():\n",
    "            for ex in features:\n",
    "                yield (\n",
    "                    {\n",
    "                         \"input_ids\": ex.input_ids,\n",
    "                         \"attention_mask\": ex.attention_mask,\n",
    "                         \"token_type_ids\": ex.token_type_ids,\n",
    "                    },\n",
    "                    ex.label,\n",
    "                )\n",
    "\n",
    "        return tf.data.Dataset.from_generator(\n",
    "            gen,\n",
    "            ({\"input_ids\": tf.int32, \"attention_mask\": tf.int32, \"token_type_ids\": tf.int32}, tf.int64),\n",
    "            (\n",
    "                {\n",
    "                    \"input_ids\": tf.TensorShape([None]),\n",
    "                    \"attention_mask\": tf.TensorShape([None]),\n",
    "                    \"token_type_ids\": tf.TensorShape([None]),\n",
    "                },\n",
    "                tf.TensorShape([]),\n",
    "            ),\n",
    "        )\n",
    "\n",
    "    return features\n",
    "\n",
    "\n",
    "class MrpcProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the MRPC data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence1\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"sentence2\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        logger.info(\"LOOKING AT {}\".format(os.path.join(data_dir, \"train.tsv\")))\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"0\", \"1\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, i)\n",
    "            text_a = line[3]\n",
    "            text_b = line[4]\n",
    "            label = line[0]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class MnliProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the MultiNLI data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"premise\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"hypothesis\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev_matched.tsv\")), \"dev_matched\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"contradiction\", \"entailment\", \"neutral\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            text_a = line[8]\n",
    "            text_b = line[9]\n",
    "            label = line[-1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class MnliMismatchedProcessor(MnliProcessor):\n",
    "    \"\"\"Processor for the MultiNLI Mismatched data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev_mismatched.tsv\")), \"dev_matched\")\n",
    "\n",
    "\n",
    "class ColaProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the CoLA data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence\"].numpy().decode(\"utf-8\"),\n",
    "            None,\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"0\", \"1\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            guid = \"%s-%s\" % (set_type, i)\n",
    "            text_a = line[3]\n",
    "            label = line[1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class Sst2Processor(DataProcessor):\n",
    "    \"\"\"Processor for the SST-2 data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence\"].numpy().decode(\"utf-8\"),\n",
    "            None,\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"0\", \"1\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, i)\n",
    "            text_a = line[0]\n",
    "            label = line[1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class StsbProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the STS-B data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence1\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"sentence2\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [None]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            text_a = line[7]\n",
    "            text_b = line[8]\n",
    "            label = line[-1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class QqpProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the QQP data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"question1\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"question2\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"0\", \"1\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            try:\n",
    "                text_a = line[3]\n",
    "                text_b = line[4]\n",
    "                label = line[5]\n",
    "            except IndexError:\n",
    "                continue\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class QnliProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the QNLI data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"question\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"sentence\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev_matched\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"entailment\", \"not_entailment\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            text_a = line[1]\n",
    "            text_b = line[2]\n",
    "            label = line[-1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class RteProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the RTE data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence1\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"sentence2\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"entailment\", \"not_entailment\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            text_a = line[1]\n",
    "            text_b = line[2]\n",
    "            label = line[-1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "\n",
    "class WnliProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the WNLI data set (GLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"sentence1\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"sentence2\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"train.tsv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_tsv(os.path.join(data_dir, \"dev.tsv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"0\", \"1\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, line[0])\n",
    "            text_a = line[1]\n",
    "            text_b = line[2]\n",
    "            label = line[-1]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=label))\n",
    "        return examples\n",
    "\n",
    "class BoolqProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the BoolQ data set (SuperGLUE version).\"\"\"\n",
    "\n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"passage\"].numpy().decode(\"utf-8\"),\n",
    "            tensor_dict[\"question\"].numpy().decode(\"utf-8\"),\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "        )\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        logger.info(\"LOOKING AT {}\".format(os.path.join(data_dir, \"train.jsonl\")))\n",
    "        with open(os.path.join(data_dir,\"train.jsonl\"),\"r\") as f:\n",
    "            return self._create_examples(f.read().splitlines(), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        with open(os.path.join(data_dir,\"val.jsonl\"),\"r\") as f:\n",
    "            return self._create_examples(f.read().splitlines(), \"val\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\"False\", \"True\"]\n",
    "\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            line=json.loads(line)\n",
    "            guid = \"%s-%s\" % (set_type,line[\"idx\"])\n",
    "            text_a = line[\"passage\"]\n",
    "            text_b = line[\"question\"]\n",
    "            label = line[\"label\"]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_b, label=str(label)))\n",
    "        return example\n",
    "\n",
    "class EmojiProcessor(DataProcessor):\n",
    "    \"\"\"Processor for the Emoji data set.\"\"\"\n",
    "    \n",
    "    def get_example_from_tensor_dict(self, tensor_dict):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return InputExample(\n",
    "            tensor_dict[\"idx\"].numpy(),\n",
    "            tensor_dict[\"passage\"].numpy().decode(\"utf-8\"),\n",
    "            None,\n",
    "            str(tensor_dict[\"label\"].numpy()),\n",
    "    )\n",
    "\n",
    "    def _read_csv(cls, input_file, quotechar=None):\n",
    "        with open(input_file, \"r\") as f:\n",
    "            reader = csv.reader(f, quotechar=quotechar)\n",
    "            lines = []\n",
    "            for line in reader:\n",
    "                if sys.version_info[0] == 2:\n",
    "                    line = list(unicode(cell, 'utf-8') for cell in line)\n",
    "                lines.append(line)\n",
    "            return lines\n",
    "\n",
    "    def get_train_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_csv(os.path.join(data_dir, \"train.csv\")), \"train\")\n",
    "\n",
    "    def get_dev_examples(self, data_dir):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return self._create_examples(self._read_csv(os.path.join(data_dir, \"val.csv\")), \"dev\")\n",
    "\n",
    "    def get_labels(self):\n",
    "        \"\"\"See base class.\"\"\"\n",
    "        return [\":smiling_face_with_smiling_eyes:\", \":broken_heart:\", \":face_with_tears_of_joy:\", \":crying_face:\", \":grinning_face_with_sweat:\", \":red_heart:\",\":smiling_face_with_heart-eyes:\",\":rolling_on_the_floor_laughing:\", \":blue_heart:\", \":beaming_face_with_smiling_eyes:\", \":two_hearts:\",\":sparkling_heart:\", \":face_blowing_a_kiss:\", \":fire:\", \":folded_hands:\", \":clapping_hands:\", \":loudly_crying_face:\", \":thinking_face:\", \":heart_suit:\", \":thumbs_up:\"]\n",
    "    def _create_examples(self, lines, set_type):\n",
    "        \"\"\"Creates examples for the training and dev sets.\"\"\"\n",
    "        examples = []\n",
    "        for (i, line) in enumerate(lines):\n",
    "            if i == 0:\n",
    "                continue\n",
    "            guid = \"%s-%s\" % (set_type, i)\n",
    "            text_a = line[1]\n",
    "            label =line[0]\n",
    "            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=str(label)))\n",
    "        return examples\n",
    "\n",
    "glue_tasks_num_labels = {\n",
    "    \"cola\": 2,\n",
    "    \"mnli\": 3,\n",
    "    \"mrpc\": 2,\n",
    "    \"sst-2\": 2,\n",
    "    \"sts-b\": 1,\n",
    "    \"qqp\": 2,\n",
    "    \"qnli\": 2,\n",
    "    \"rte\": 2,\n",
    "    \"wnli\": 2,\n",
    "    \"boolq\": 2,\n",
    "    \"emoji\": 20,\n",
    "    }\n",
    "\n",
    "glue_processors = {\n",
    "    \"cola\": ColaProcessor,\n",
    "    \"mnli\": MnliProcessor,\n",
    "    \"mnli-mm\": MnliMismatchedProcessor,\n",
    "    \"mrpc\": MrpcProcessor,\n",
    "    \"sst-2\": Sst2Processor,\n",
    "    \"sts-b\": StsbProcessor,\n",
    "    \"qqp\": QqpProcessor,\n",
    "    \"qnli\": QnliProcessor,\n",
    "    \"rte\": RteProcessor,\n",
    "    \"wnli\": WnliProcessor,\n",
    "    \"boolq\":BoolqProcessor,\n",
    "    \"emoji\":EmojiProcessor,\n",
    "}\n",
    "\n",
    "glue_output_modes = {\n",
    "    \"cola\": \"classification\",\n",
    "    \"mnli\": \"classification\",\n",
    "    \"mnli-mm\": \"classification\",\n",
    "    \"mrpc\": \"classification\",\n",
    "    \"sst-2\": \"classification\",\n",
    "    \"sts-b\": \"regression\",\n",
    "    \"qqp\": \"classification\",\n",
    "    \"qnli\": \"classification\",\n",
    "    \"rte\": \"classification\",\n",
    "    \"wnli\": \"classification\",\n",
    "    \"boolq\":\"classification\",\n",
    "    \"emoji\":\"classification\"\n",
    "}"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.4"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
