from __future__ import division 

import pandas as pd
import numpy as np

class Compare(object):
	"""A class to make comparing of records fields easier. It can be used to compare fields of the record pairs. """

	def __init__(self, A=None, B=None, pairs=None):

		self.A = A
		self.B = B
		self.pairs = pairs

		self.comparison_vectors = None

	def exact(self, *args, **kwargs):
		"""
		exact(s1, s2, missing_value=0, output='any')

		Compare the record pairs exactly.

		:param s1: Series or DataFrame to compare all fields. 
		:param s2: Series or DataFrame to compare all fields. 
		:param missing_value: The value for a comparison with a missing value. Default 0.
		:param output: Default 'any'. This holds only for comparing dataframes.
		:param return_agreement_values: If return_agreement_values is True, each agreeing comparison returns the value instead of 1. Default False.		

		:return: A Series with comparison values.
		:rtype: pandas.Series

		"""

		return self.compare(exact, *args, **kwargs)

	def numerical(self, *args, **kwargs):
		"""
		numerical(s1, s2, window, missing_value=0)

		Compare numerical values with a tolerance window.

		:param s1: Series or DataFrame to compare all fields. 
		:param s2: Series or DataFrame to compare all fields. 
		:param missing_value: The value for a comparison with a missing value. Default 0.
		:param window: The window size. Can be a tuple with two values or a single number. 

		:return: A Series with comparison values.
		:rtype: pandas.Series

		"""

		return self.compare(window_numerical, *args, **kwargs)

	def fuzzy(self, *args, **kwargs):
		"""
		fuzzy(s1, s2, method='levenshtein', threshold=None, missing_value=0)

		Compare string values with a similarity approximation. 

		:param s1: Series or DataFrame to compare all fields. 
		:param s2: Series or DataFrame to compare all fields. 
		:param method: A approximate string comparison method. Options are ['jaro', 'jarowinkler', 'levenshtein', 'damerau_levenshtein']. Default: 'levenshtein'
		:param threshold: A threshold value. All approximate string comparisons higher or equal than this threshold are 1. Otherwise 0.  
		:param missing_value: The value for a comparison with a missing value. Default 0.

		:return: A Series with similarity values. Values equal or between 0 and 1.
		:rtype: pandas.Series

		Note: For this function is the package 'jellyfish' required. 

		"""
		return self.compare(fuzzy, *args, **kwargs)

	def geo(self, *args, **kwargs):
		"""
		geo(X1, Y1, X2, Y2, radius=20, disagreement_value = -1, missing_value=-1)

		Compare geometric coordinates with a tolerance window.

		:param X1: Series with X-coordinates
		:param Y1: Series with Y-coordinates
		:param X2: Series with X-coordinates
		:param Y2: Series with Y-coordinates
		:param missing_value: The value for a comparison with a missing value. Default -1.
		:param disagreement_value: The value for a disagreeing comparison. Default -1.

		:param compare_method: levestein

		:return: A Series with comparison values.
		:rtype: pandas.Series
		"""

		return self.compare(compare_geo, *args, **kwargs)

	def compare(self, comp_func, *args, **kwargs):
		"""Compare the records given. 
		
		:param comp_func: A list, dict or tuple of comparison tuples. Each tuple contains a comparison function, the fields to compare and the arguments. 
		
		:return: A DataFrame with compared variables.
		:rtype: standardise.DataFrame
		"""
		
		if isinstance(comp_func, (list, dict, tuple)):
			
			for t in comp_func:
				# func is a tuple of args and kwargs
				
				func = t[0]
				args_func = t[1]
				kwargs_func = t[2]
				
				self._append(self._compare_column(func, *args_func, **kwargs_func))
				
		else:
			
			name = kwargs.pop('name', None)
			self._append(comp_func(*args, **kwargs), name=name)
			
		return self.comparison_vectors
		
	def _append(self, comp_vect, name=None, store=True, *args, **kwargs):

		if store:

			comp_vect.name = name

			try: 
				self.comparison_vectors[name] = pd.Series(comp_vect)
			except:
				self.comparison_vectors = pd.DataFrame(comp_vect)

		return self.comparison_vectors

def _missing(s1, s2):

	return (pd.DataFrame(s1).isnull().all(axis=1) | pd.DataFrame(s2).isnull().all(axis=1))

def exact(s1, s2, missing_value=0, disagreement_value=0, output='any', return_agreement_values=False):
	"""
	Compare two series or dataframes exactly on all fields. 
	"""

	df1 = pd.DataFrame(s1)
	df2 = pd.DataFrame(s2)

	# Only when one of the input variables is a DataFrame
	if len(list(df1)) > 1 or len(list(df2)) > 1:

		compare = pd.DataFrame([(df1[col1] == df2[col2]) for col2 in list(df2) for col1 in list(df1)]).T

		# Any of the agreeing comparisons
		if output == 'any':
			compare = compare.any(axis=1)
			compare = compare.astype(int)

		# Max of the comparisons
		elif output == 'max':
			compare = compare.astype(int)
			compare = compare.max(axis=1)

		# Sum of the comparison vectors
		elif output == 'sum':
			compare = compare.sum(axis=1)

		# Unknown method
		else:
			raise ValueError('Unknown output method.')

	else:

		if not return_agreement_values:
			compare = (s1 == s2)
			compare = compare.astype(int)
		else:
			compare = s1.copy()
			compare.loc[(s1 != s2)] = disagreement_value

	# Only for missing values
	compare[_missing(df1, df2)] = missing_value

	return compare

def window_numerical(s1, s2, window, missing_value=0):

	if isinstance(window, (list, tuple)):
		compare = (((s1-s2) <= window[1]) & ((s1-s2) >= window[0])).astype(int)
	else:
		compare = (((s1-s2) <= window) & ((s1-s2) >= window)).astype(int)

	compare[_missing(s1, s2)] = missing_value 

	return compare

def compare_geo(X1, Y1, X2, Y2, radius=None, missing_value=9):

	distance = np.sqrt(np.power(X1-X2,2)+np.power(Y1-Y2,2))

	comp = (distance <= radius).astype(int)

	comp[_missing(X1, X2)] = missing_value
	comp[_missing(Y1, Y2)] = missing_value

	return comp 

def fuzzy(s1,s2, method='levenshtein', threshold=None, missing_value=0):

	try:
		import jellyfish
	except ImportError:
		print "Install jellyfish to use approximate string comparison."

	series = pd.concat([s1, s2], axis=1)

	if method == 'jaro':
		approx = series.apply(lambda x: jellyfish.jaro_distance(x[0], x[1]) if pd.notnull(x[0]) and pd.notnull(x[1]) else np.nan, axis=1)
	
	elif method == 'jarowinkler':
		approx = series.apply(lambda x: jellyfish.jaro_winkler(x[0], x[1]) if pd.notnull(x[0]) and pd.notnull(x[1]) else np.nan, axis=1)
	
	elif method == 'levenshtein':
		approx = series.apply(lambda x: jellyfish.levenshtein_distance(x[0], x[1])/np.max([len(x[0]),len(x[1])]) if pd.notnull(x[0]) and pd.notnull(x[1]) else np.nan, axis=1)
		approx = 1 - approx

	elif method == 'damerau_levenshtein':
		approx = series.apply(lambda x: jellyfish.damerau_levenshtein_distance(x[0], x[1])/np.max([len(x[0]),len(x[1])]) if pd.notnull(x[0]) and pd.notnull(x[1]) else np.nan, axis=1)
		approx = 1 - approx

	else:
		raise ValueError('The method %s is not found.' % method)

	if threshold is not None:
		comp = (approx >= threshold).astype(int)
	else:
		comp = approx

	# Only for missing values
	compare[_missing(s1, s2)] = missing_value

	return compare

def window(s1, s2, window, missing_value=0, disagreement_value=0, sim_func=None):

	diff = s2-s1

	w = window if isinstance(window, (list, tuple)) else (window,window)

	if sim_func == None:
		sim = diff[(diff <= window[1]) & (diff >= window[0])]

	elif sim_func == 'linear':
		pass

	else:
		compare = (((s1-s2) <= window) & ((s1-s2) >= window)).astype(int)

	compare[_missing(s1, s2)] = missing_value 

	return compare

def math_window(s1, s2, sim_func):

	return 

def bin_compare_geq(cat1, cat2, missing_value=0):

	# compare
	comp = (cat1 >= cat2).astype(int)
	comp.ix[_missing(cat1, cat2)] = missing_value 

	return comp

def compare_levels(s1, s2, freq, split=np.array([1, 5, 10, 20, 50, 100, np.inf])):

	comp = freq.copy()

	comp.fillna(0, inplace=True)
	comp.loc[(s1 != s2)] = 0

	for sp in range(0, len(split)-1):
		comp.loc[(comp < split[sp+1]) & (comp >= split[sp])] = split[sp]

	return comp

class CompareException(Exception):
	pass


