from database import update_album_tags, update_album_ratings, update_song_ratings, read_album_tags
from tagmatrix import convert_to_matrix, convert_to_npmi, autoencode
from random import randrange

for i in range(10000):
  update_album_tags(str(randrange(100)), str(randrange(100)), str(randrange(100)))
matrix = convert_to_matrix(read_album_tags())
npmi_matrix = convert_to_npmi(matrix)
encoded_space = autoencode(npmi_matrix)
print find_distance_matrix(matrix, encoded_space)
