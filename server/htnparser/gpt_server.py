#!/home/lane/miniconda3/bin/python

from torch.nn.functional import softmax
from transformers import GPTNeoXForCausalLM, GPTNeoXTokenizerFast, AutoModelForCausalLM, AutoTokenizer
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import sys
import deepspeed
import torch
import traceback

# model_type = './gpt-j-hf'
# model_type = 'EleutherAI/gpt-j-6B'
model_type = 'EleutherAI/gpt-neox-20b'
# model_type = 'facebook/opt-30b'

class GPTServer:
	def __init__(self, model_type, temp=0.2, rep_pen=1.1):
		# self.tokenizer = GPTNeoXTokenizerFast.from_pretrained('EleutherAI/gpt-neox-20b')

		self.WINDOW_SIZE = 1024 if model_type in ['distilgpt2', 'gpt2-xl', 'gpt2-large', 'gpt2-medium'] else 2048

		self.model_type = model_type

		# print('loading word2vec model...')

		# self.word2vec_model = gensim.models.KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

		# print('done')

		print('loading transformer model %s...' % (model_type))

		model = None
		self.tokenizer = None
		if model_type == 'distilgpt2':
			self.tokenizer = AutoTokenizer.from_pretrained('distilgpt2')
			model = GPT2DoubleHeadsModel.from_pretrained(model_type)
			model.to('cuda:0')
		elif model_type == 'gpt2-large' or model_type == 'gpt2-xl' or model_type == 'gpt2-medium':
			self.tokenizer = AutoTokenizer.from_pretrained(model_type)
			model = GPT2DoubleHeadsModel.from_pretrained(model_type)
			model.to('cuda:0')
		elif model_type == 'EleutherAI/gpt-neox-20b':
			self.tokenizer = AutoTokenizer.from_pretrained(model_type)
			model = AutoModelForCausalLM.from_pretrained(model_type, torch_dtype=torch.float16, device_map='auto', max_memory={'cpu': '0GIB', 0: '40GIB', 1: '0GIB', 2: '0GIB', 3: '0GIB'})
		elif model_type == 'facebook/opt-30b':
			self.tokenizer = AutoTokenizer.from_pretrained(model_type)
			model = AutoModelForCausalLM.from_pretrained(model_type, device_map='auto', load_in_8bit=True, max_memory={'cpu': '0GIB', 0: '40GIB', 1: '0GIB', 2: '0GIB', 3: '0GIB'})
			# print('deepspeeding...')
			# ds_engine = deepspeed.init_inference(model, replace_method='auto', replace_with_kernel_inject=True)
			# print('done')
			# model = ds_engine.module
		else:
			# model = GPTNeoXForCausalLM.from_pretrained(model_type).half().eval().to('cuda:0')
			# self.tokenizer = AutoTokenizer.from_pretrained(model_type)
			# model = AutoModelForCausalLM.from_pretrained(model_type).eval().to('cuda:0')
			# model.half().to('cuda:0')
			self.tokenizer = AutoTokenizer.from_pretrained(model_type)
			model = AutoModelForCausalLM.from_pretrained(model_type)
			print('deepspeeding...')
			ds_engine = deepspeed.init_inference(model, replace_method='auto', replace_with_kernel_inject=True)
			print('done')
			model = ds_engine.module

		self.model = model

		print('done')
		

	def get_model_name(self):
		return self.model_type

	def gen(self, string, temp, rep_pen, max_length):
		ids = self.tokenizer(string, return_tensors='pt').input_ids.to('cuda:0')
		res = None
		if temp > 0:
			res = self.model.generate(ids, do_sample=True, temperature=temp, max_length=max_length, repetition_penalty=rep_pen, pad_token_id=50256)
		else:
			res = self.model.generate(ids, max_length=max_length, repetition_penalty=rep_pen, pad_token_id=50256)

		return self.tokenizer.batch_decode(res)[0]

	def _get_forward_info(self, string, get_all=False):
		try:
			ids = self.tokenizer(string, return_tensors='pt').input_ids
			if len(ids.squeeze()) > self.WINDOW_SIZE:
				return None
			ids = ids.to('cuda:0')

			outp = self.model(ids, output_hidden_states=True)

			# take last layer
			states = outp.hidden_states[-1].to('cpu').tolist()

			ids = ids.to('cpu')
			logits = outp.logits.detach().float().to('cpu')
			del outp

			torch.cuda.empty_cache()
			torch.cuda.synchronize()

			logprobs = []
			for i in range(len(logits[0])):
				tok_logprobs = torch.log(softmax(logits[0][i].squeeze(), dim=0))
				tok = ids.squeeze()[i]
				logprobs.append(tok_logprobs[int(tok)].tolist())

			# batch size is 1
			states = states[0]

			if not get_all:
				# take last token's states only
				# states = states[-1]

				# average all token states
				states = torch.tensor(states).mean(dim=0).tolist()

			return (states, logprobs)
		except:
			print(sys.exc_info())
			traceback.print_tb(sys.exc_info()[2])
			return None

	def get_hidden_states(self, string):
		return self._get_forward_info(string, get_all=False)[0]

	def get_all_hidden_states(self, string):
		return self._get_forward_info(string, get_all=True)[0]

	def get_logprobs(self, string):
		return self._get_forward_info(string)[1]

	def get_avg_logprob(self, string):
		logprobs = self.get_logprobs(string)
		return sum(logprobs)*1.0/len(logprobs)

	def gen_with_logprobs(self, string, temp, rep_pen, max_length):
		ids = self.tokenizer(string, return_tensors='pt').input_ids.to('cuda:0')

		res = None
		if temp > 0:
			res = self.model.generate(ids, do_sample=True, temperature=temp, max_length=max_length, repetition_penalty=rep_pen, pad_token_id=50256, return_dict_in_generate=True, output_scores=True)
		else:
			res = self.model.generate(ids, max_length=max_length, repetition_penalty=rep_pen, pad_token_id=50256, return_dict_in_generate=True, output_scores=True)

		toks = [int(tok) for tok in res.sequences.squeeze()[len(ids.squeeze()):]]
		scores = res.scores
		tok_logprobs = []
		for i in range(len(toks)):
			logits = scores[i]
			tok = toks[i]
			logprobs = torch.log(softmax(logits.squeeze(), dim=0))
			tok_logprobs.append(float(logprobs[tok]))
			

		gen_text = self.tokenizer.batch_decode(res.sequences)[0]

		return (gen_text, toks, tok_logprobs)

class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)

if __name__ == '__main__':
	if len(sys.argv) > 1:
		model_type = sys.argv[1]

	gpt_server = GPTServer(model_type)

	def gen(string, temp, rep_pen, max_length):
		return gpt_server.gen(string, temp, rep_pen, max_length)

	def get_hidden_states(string):
		return gpt_server.get_hidden_states(string)

	def get_all_hidden_states(string):
		return gpt_server.get_all_hidden_states(string)

	def get_logprobs(string):
		return gpt_server.get_logprobs(string)

	def gen_with_logprobs(string, temp, rep_pen, max_length):
		return gpt_server.gen_with_logprobs(string, temp, rep_pen, max_length)

	def get_avg_logprob(string):
		return gpt_server.get_avg_logprob(string)

	def get_model_name():
		return gpt_server.get_model_name()

	with SimpleXMLRPCServer(('localhost', 8000), requestHandler=RequestHandler) as server:
		server.register_introspection_functions()

		server.register_function(gen)
		server.register_function(gen_with_logprobs)
		server.register_function(get_hidden_states)
		server.register_function(get_all_hidden_states)
		server.register_function(get_logprobs)
		server.register_function(get_avg_logprob)
		server.register_function(get_model_name)

		print('gpt server started')
		server.serve_forever()
