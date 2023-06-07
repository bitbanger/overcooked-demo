import argparse
import hashlib
import openai
import os
import sys
# import torch
import xmlrpc.client

class GPTCompleter:
	def __init__(self, local_model=None):
		if local_model is not None:
			try:
				self.server = xmlrpc.client.ServerProxy('http://localhost:8000')
			except:
				print("Couldn't connect to local GPT server.")
				quit()
			try:
				from transformers import AutoTokenizer
				self.tokenizer = AutoTokenizer.from_pretrained(local_model)
			except:
				print("Couldn't initialize tokenizer for model '%s'." % (local_model,))
				quit()

			server_model_name = self.server.get_model_name()
			if local_model != server_model_name:
				print("Local model '%s' is different from server model '%s'." % (local_model, server_model_name))
				quit()

			self.get_completion = self.get_local_completion
		else:
			self.init_openai_api()
			self.get_completion = self.get_api_completion
			self.cache = dict()
			for fn in os.listdir('api_cache/'):
				with open('api_cache/%s' % fn, 'r') as f:
					self.cache[int(fn)] = f.read()

	def init_openai_api(self):
		try:
			with open('openai-key', 'r') as f:
				openai.api_key = f.read().strip()
		except:
			print("Couldn't open file 'openai-key' for reading.")
			quit()
		

	def get_local_completion(self, prompt, temp=0.0, rep_pen=1.0, max_length=256):
		input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
		(completion, toks, logprobs) = self.server.gen_with_logprobs(prompt, temp, rep_pen, min(2048, len(input_ids.squeeze())+max_length))

		return completion.encode('utf-8').decode('utf-8')[len(prompt):]

	def get_api_completion(self, prompt, temp=0.0, rep_pen=0.0, max_length=256, stop=None):
		if temp == 0:
			key = hash((prompt, rep_pen, max_length, stop))
			key = int(hashlib.md5(str((prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
			if key not in self.cache:
				self.cache[key] = openai.Completion.create(
					engine='text-davinci-003',
					prompt=prompt,
					max_tokens=max_length,
					temperature=temp,
					frequency_penalty=rep_pen,
					stop=None,
				).choices[0].text
				with open('api_cache/%d' % key, 'w') as f:
					f.write(self.cache[key])
			return self.cache[key]
		else:
			return openai.Completion.create(
				engine='text-davinci-003',
				prompt=prompt,
				max_tokens=max_length,
				temperature=temp,
				frequency_penalty=rep_pen,
				stop=None,
			).choices[0].text

	def get_chat_gpt_completion(self, prompt, temp=0.0, rep_pen=0.0, max_length=256, stop=None, retries=5):
		res = None
		for _ in range(retries):
			try:
				res = self.get_chat_gpt_completion_helper(prompt, temp=temp, rep_pen=rep_pen, max_length=max_length, stop=stop)
			except openai.error.RateLimitError:
				continue

			break

		return res

	def get_chat_gpt_completion_helper(self, prompt, temp=0.0, rep_pen=0.0, max_length=256, stop=None):
		print('.', end='')
		# prompt_msgs = [x.strip() for x in prompt.split('***') if len(x.strip()) > 0]
		prompt_msgs = [x.strip() for x in prompt.split('***')]
		annotated_msgs = []
		role = 'user'
		other_role = 'assistant'
		for msg in prompt_msgs[::-1]:
			if len(msg) > 0:
				annotated_msgs = [{'role': role, 'content': msg.strip()}] + annotated_msgs
			(role, other_role) = (other_role, role)

		# print('RAW MSGS:')
		# print(annotated_msgs)

		if temp == 0:
			key = hash(('chat', prompt, rep_pen, max_length, stop))
			key = int(hashlib.md5(str(('chat', prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
			if key not in self.cache:
				self.cache[key] = openai.ChatCompletion.create(
					model='gpt-3.5-turbo',
					messages=annotated_msgs,
					max_tokens=max_length,
					temperature=temp,
					frequency_penalty=rep_pen,
					stop=stop,
				).choices[0].message.content
				with open('api_cache/%d' % key, 'w') as f:
					f.write(self.cache[key])
			# print('RESP:')
			# print(self.cache[key])
			return self.cache[key]
		else:
			res = openai.ChatCompletion.create(
				model='gpt-3.5-turbo',
				messages=annotated_msgs,
				max_tokens=max_length,
				temperature=temp,
				frequency_penalty=rep_pen,
				stop=stop,
			).choices[0].message.content
			# print('RESP:')
			# print(res)
			return res
