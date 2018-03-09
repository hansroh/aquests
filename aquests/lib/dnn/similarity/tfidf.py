from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_selection import VarianceThreshold, SelectKBest, SelectPercentile, chi2
from sklearn.metrics.pairwise import cosine_similarity
import sklearn.cluster as cl
import numpy as np
import pandas as pd
import sys, os
import time
from pprint import pprint as pp

# TF로 벡터화된 샘플들을 sklearn과 numpy로 TFIDF 행렬연산
class Samples:
	def __init__ (self, bow, labels, samples):
		self.bow = bow
		self.labels = labels
		# reversing for get term by id
		self.names = dict((v,k) for k,v in bow.items())
		self.samples = samples
		self.matrix = None
		self.diminished_dfm = None
	
	def measure (self, index = 0, threshold = 0.9):
		assert self.diminished_dfm is not None, 'please, diminish first'		
		distances = cosine_similarity (self.diminished_dfm [index:index + 1], self.diminished_dfm)
		ids = np.argsort(distances [0])[::-1]
		return self.labels [index], [(self.labels [id], distances [0][id]) for id in ids if id != index and distances [0][id] >= threshold]
	
	def measure_all (self, threshold = 0.9):
		assert self.diminished_dfm is not None, 'please, diminish first'		
		distances = cosine_similarity (self.diminished_dfm, self.diminished_dfm)
		results = []
		for index in range (len (distances)):
			current_row = distances [index]
			ids = np.argsort(current_row)[::-1]
			result = [(self.diminished_dfm.index [id], current_row [id]) for id in ids if id != index and current_row [id] >= threshold]
			results.append ((self.labels [index], result))
		return results
	
	def diminish (self, feats):	
		# 모든 문헌을 선택된 n개의 피쳐들을 선택하여 하여 문서벡터를 축소
		# one feat: (term, term index, score)
		terms = self.bow.items ()
		columns = [k for k, v in sorted (terms, key = lambda x: x [1])]		
		dfm = pd.DataFrame (self.matrix.toarray (), index = self.labels, columns = columns)
		diminished_dfm = dfm.iloc [:, [feat [1] for feat in feats]]
		# pandas DataFrame 형태로 리턴
		# refilter non zero sum vector		
		diminished_dfm = diminished_dfm [diminished_dfm.sum (1) > 0.0]
		self.diminished_dfm = diminished_dfm
		
		# clearing memory
		self.matrix = None		
		self.labels = None
		self.names = None
		self.bow = None
		return diminished_dfm
	
	def to_dataframe (self):
		terms = self.bow.items ()
		columns = [k for k, v in sorted (terms, key = lambda x: x [1])]		
		return pd.DataFrame (self.matrix.toarray (), index = self.labels, columns = columns)		
		
	def transform_tfidf (self):
		if len (self.samples) == 0:
			return
		# TF 벡터 샘플들을 TFIDF 벡터로 변환
		transformer = TfidfTransformer(smooth_idf = True, norm = "l2")
		self.matrix = transformer.fit_transform (self.samples)
		return self.matrix
	
	def transform_binary (self):
		if len (self.samples) == 0:
			return
		# TF 벡터 샘플들을 Binary 벡터로 변환
		self.matrix = self.samples > 0
		self.matrix = self.samples.astype (int)		
		self.samples = None
		return self.matrix
		
	def isvalid (self):
		return self.matrix is not None


class SampleFromDF:
	def __init__ (self, df):
		self.diminished_dfm = df
		self.labels = df.index
		
	def measure (self, target = None, threshold = 0.9):
		if target is None:
			target = self.diminished_dfm
		distances = cosine_similarity (target, self.diminished_dfm)
		results = []
		for index in range (len (distances)):
			current_row = distances [index]
			ids = np.argsort(current_row)[::-1]
			row = []
			for id in ids:
				if self.labels [id] == target.index [index]:
					assert abs (1.0 - current_row [id]) < 0.001						
					continue				
				if current_row [id] >= threshold:
					row.append ((self.labels [id], current_row [id]))
			results.append ((target.index [index], row))			
		assert len (results) == len (target)		
		return results
		