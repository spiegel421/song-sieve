# Establishes, in binary fashion, whether each album has each tag based on PMI values and autoencoding.
import numpy as np
import pandas as pd
import copy
from keras.layers import Input, Dense
from keras.models import Model
from sklearn import svm

# Converts dictionaries to labeled matrices, using pandas's DataFrame class.
def convert_to_matrix(album_tag_dict):
  return pd.DataFrame(album_tag_dict).T.fillna(0)

# Generates matrix of PPMI values from matrix of counts.
def convert_to_ppmi(count_matrix):
  ppmi_matrix = copy.copy(count_matrix)
  
  for row in range(len(count_matrix.values)):
    for col in range(len(count_matrix.values[0])):
      entry = float(count_matrix.values[row][col])
      if entry == 0:
        ppmi_matrix.values[row][col] = 0.0
        continue
      else:
        prob_con = entry / count_matrix.values.sum()
        if prob_con == 1.0:
          ppmi_matrix.values[row][col] = 1.0
          continue
        else:
          prob_row = entry / count_matrix.values.sum(axis=1)[row]
          prob_col = entry / count_matrix.values.sum(axis=0)[col]
          ppmi_value = 2 ** (np.log(prob_con / (prob_row * prob_col)) + np.log(prob_con))
          ppmi_matrix.values[row][col] = ppmi_value
          
  return ppmi_matrix

# Auto-encodes PPMI matrix into 20 dimensions, using five-fold cross validation.
def autoencode(ppmi_matrix):
  original_dim = len(ppmi_matrix.values[0])
  encoding_dim = 20
  
  input = Input(shape=(original_dim,))
  encoded = Dense(encoding_dim, activation='sigmoid')(input)
  decoded = Dense(original_dim, activation='sigmoid')(encoded)
  
  autoencoder = Model(input, decoded)
  encoder = Model(input, encoded)
  encoded_input = Input(shape=(encoding_dim,))
  decoder_layer = autoencoder.layers[-1]
  decoder = Model(encoded_input, decoder_layer(encoded_input))
  
  X = ppmi_matrix.values
  autoencoder.compile(optimizer='sgd', loss='mean_squared_error')
  autoencoder.fit(X, X, validation_split=0.2, 
                  epochs=50, batch_size=10)
  
  encoded_space = pd.DataFrame(encoder.predict(ppmi_matrix.values), index=ppmi_matrix.index)
  return encoded_space

# Determines the distance of each album from each tag's hyperplane.
def find_distance_matrix(count_matrix, encoded_space):
  distance_matrix = copy.copy(count_matrix).T
  
  clf = svm.LinearSVC()
  for tag in distance_matrix.index:
    y = copy.copy(distance_matrix.loc[tag])
    y = [1 if item > 0 else 0 for item in y.values]
    clf.fit(encoded_space.values, y)
    distance_matrix.loc[tag] = clf.decision_function(encoded_space.values)
    
  return distance_matrix

# Ranks albums by distance from each tag's hyperplane.
def rank_distance_matrix(distance_matrix):
  sorted_by_distance = {}
  for tag in distance_matrix.index:
    sorted_by_distance[tag] = sorted(distance_matrix.columns, 
                                     key=lambda album: distance_matrix.loc[tag][album], 
                                     reverse=True)
    
  ranked_matrix = copy.copy(distance_matrix)
  for tag in distance_matrix.index:
    ranked_matrix.loc[tag] = [sorted_by_distance[tag].index(album) + 1 for album in distance_matrix.columns]
    
  return ranked_matrix

# Finds normalized discounted cumulative gain (NDCG) for each tag.
def find_ndcg_values(ppmi_matrix, ranked_matrix):
  ndcg_values = {}
  rankings_dict = ranked_matrix.to_dict(orient='index')
  for tag in ranked_matrix.index:
    dcg = 0.0
    album_rankings = rankings_dict[tag]
    for album in album_rankings:
      dcg += ppmi_matrix.loc[album][tag] / (np.log(album_rankings[album] + 1) / np.log(2))
      
    idcg = 0.0
    sorted_relevancies = sorted(ppmi_matrix.T.loc[tag], reverse=True)
    for i in range(len(sorted_relevancies)):
      idcg += sorted_relevancies[i] / (np.log(i + 2) / np.log(2))
      
    ndcg_values[tag] = dcg / idcg
    
  return ndcg_values

# Finds binary table based on ranked matrix and tag NDCG values.
def find_binary_table(ranked_matrix, percentile, ndcg_values, cutoff_ndcg):
  interpretable_tags = []
  for tag in ndcg_values:
    if ndcg_values[tag] >= cutoff_ndcg:
      interpretable_tags.append(tag)
  
  binary_table = []
  num_albums = len(ranked_matrix.iloc[0])
  cutoff_rank = (1 - percentile) * num_albums
  rankings_dict = ranked_matrix.to_dict(orient='index')
  for tag in interpretable_tags:
    album_rankings = rankings_dict[tag]
    for album in album_rankings:
      if album_rankings[album] <= cutoff_rank:
        item = (album, tag)
        binary_table.append(item)
        
  return binary_table
