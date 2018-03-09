#--------------------------------------------------------
# Feature Selectors For Unsupervised Learning
# with TFIDF Vectors
# 2017.11.3 Hans roh
#--------------------------------------------------------

from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_selection import VarianceThreshold, SelectKBest, SelectPercentile, chi2
from sklearn.metrics.pairwise import cosine_similarity
import sklearn.cluster as cl
import numpy as np
import pandas as pd
import pickle
import sys, os
import time
from pprint import pprint as pp

class Variant:		
	def __init__ (self, samples):
		self.samples = samples
		
	def select (self, top_n = 6000, min_tfidf = 0.1, reverse = False):	
		# TFIDF 분산도로 변별력이 높은 단어들만 선택
		D = self.samples.matrix.toarray ()
		
		scores = np.var (D, axis = 0)
		# shape check
		assert len (scores) == len (D [0])
		
		ids = np.argsort(scores)[::-1]
		if reverse:
			# 스코어가 낮은 단어를 보려면 True
			topn_ids = ids [-top_n:]
		else:
			topn_ids = ids [:top_n]
		
		top_feats = [(self.samples.names [i], i, scores [i]) for i in topn_ids]
		print ("{} features was selected".format (len (top_feats)))
		# 스코어가 높은 상위 top_n
		return top_feats
		

class ClusterMaxPool (Variant):	
	def select (self, top_n = 6000, min_tfidf = 0.1, reverse = False):	
		# https://stats.stackexchange.com/questions/266220/tfidf-for-feature-selection-method-for-unlabeled-text-documents
		# Term을 TFIDF covariance로 클러스터링 한 후, 각 그룹에서 MAX TF Term 을 선택
		# 좋은 아이디어인데, 비인간적으로 너무 느림
		# 유효 DF 렌지를 대폭 줄여야, 일단 보류
		
		D = self.samples.matrix.toarray ()
		covar = np.cov (D, rowvar = False)	
		k_means = cl.KMeans(init='k-means++', n_clusters = top_n, n_init=10)
		k_means.fit (covar)
		
		CS = {}
		for i, c in enumerate (k_means.labels_):
			if c not in CS:
				CS [c] = []			
			CS [c].append (self.samples.names [i])
		pp (CS)


