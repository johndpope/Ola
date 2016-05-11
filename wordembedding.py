import tensorflow as tf
import data_utils
import numpy as np
import collections
import random
import math

vocabulary_size = 200
embedding_size = 128
num_sampled = 22
num_skips = 2
data_index = 0
batch_size=128
skip_window=1
num_movie_scripts = 4

# Step 3: Function to generate a training batch for the skip-gram model.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!! Compare with tensorflows data
def generate_batch(batch_size, num_skips, skip_window):
	global data_index
	assert batch_size % num_skips == 0
	assert num_skips <= 2 * skip_window
	batch = np.ndarray(shape=(batch_size), dtype=np.int32)
	labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
	span = 2 * skip_window + 1 # [ skip_window target skip_window ]
	buffer = collections.deque(maxlen=span)
	for _ in range(span):
		buffer.append(data[data_index])
		data_index = (data_index + 1) % len(data)
	for i in range(batch_size // num_skips):
		target = skip_window  # target label at the center of the buffer
		targets_to_avoid = [ skip_window ]
		for j in range(num_skips):
			while target in targets_to_avoid:
				target = random.randint(0, span - 1)
			targets_to_avoid.append(target)
			batch[i * num_skips + j] = buffer[skip_window]
			labels[i * num_skips + j, 0] = buffer[target]
		buffer.append(data[data_index])
		data_index = (data_index + 1) % len(data)
	return batch, labels


def generateEncodedFile(filename, tokenized_array):
	f = open(filename, 'w')
	print tokenized_array[:10]

	for sentence in tokenized_array:
		encoded_sentence = ""
		for word in sentence:
			#print word
			if word in dictionary:
				encoded_word = dictionary[word]
			else:
				encoded_word = dictionary['UNK']
			encoded_sentence += str(encoded_word) + " "
		print sentence
		encoded_sentence = encoded_sentence[:-1]
		# Write sentence to file with linjeskift
		f.write(encoded_sentence + '\n')
		#print encoded_sentence

	f.close()





# Generate dictionary for dataset
tokenized_data = data_utils.read_data(num_movie_scripts)
print '-------- tokenized_data'
print tokenized_data[:10]
data, count, dictionary, reverse_dictionary = data_utils.build_dataset(tokenized_data, vocabulary_size)

print '-------- data'
print data
print '-------- count'
print count
print '-------- dictionary'
data_utils.print_dic(dictionary, 5)
print dictionary
print '-------- reverse_dictionary'
data_utils.print_dic(reverse_dictionary, 5)
print reverse_dictionary
print '-------- generateEncodedFile'
tokenized_sentences = data_utils.get_sentences(num_movie_scripts)
# Generate file
generateEncodedFile('X_train_for_3_scripts', tokenized_sentences)
print "FERDI"

"""
batch, labels = generate_batch(batch_size, num_skips, skip_window)

print '--------- batch'
print batch
print '--------- labels'
print labels

for i in range(8):
  print(batch[i], '->', labels[i, 0])
  print(reverse_dictionary[batch[i]], '->', reverse_dictionary[labels[i, 0]])



# Step 4: Build and train a skip-gram model.

batch_size = 128
embedding_size = 128  # Dimension of the embedding vector.
skip_window = 1       # How many words to consider left and right.
num_skips = 2         # How many times to reuse an input to generate a label.

# We pick a random validation set to sample nearest neighbors. Here we limit the
# validation samples to the words that have a low numeric ID, which by
# construction are also the most frequent.
valid_size = 16     # Random set of words to evaluate similarity on.
valid_window = 100  # Only pick dev samples in the head of the distribution.
valid_examples = np.random.choice(valid_window, valid_size, replace=False)
num_sampled = 50    # Number of negative examples to sample.

graph = tf.Graph()

with graph.as_default():

	# Input data.
	train_inputs = tf.placeholder(tf.int32, shape=[batch_size])
	train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
	valid_dataset = tf.constant(valid_examples, dtype=tf.int32)

	# Ops and variables pinned to the CPU because of missing GPU implementation
	with tf.device('/cpu:0'):
		# Look up embeddings for inputs.
		embeddings = tf.Variable(tf.random_uniform([vocabulary_size, embedding_size], -1.0, 1.0))
		embed = tf.nn.embedding_lookup(embeddings, train_inputs)

		# Construct the variables for the NCE loss
		nce_weights = tf.Variable(tf.truncated_normal([vocabulary_size, embedding_size],stddev=1.0 / math.sqrt(embedding_size)))
		nce_biases = tf.Variable(tf.zeros([vocabulary_size]))

		# Compute the average NCE loss for the batch.
		# tf.nce_loss automatically draws a new sample of the negative labels each
		# time we evaluate the loss.
		loss = tf.reduce_mean( tf.nn.nce_loss(nce_weights, nce_biases, embed, train_labels, num_sampled, vocabulary_size))

		# Construct the SGD optimizer using a learning rate of 1.0.
		optimizer = tf.train.GradientDescentOptimizer(1.0).minimize(loss)

		# Compute the cosine similarity between minibatch examples and all embeddings.
		norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keep_dims=True))
		normalized_embeddings = embeddings / norm
		valid_embeddings = tf.nn.embedding_lookup( normalized_embeddings, valid_dataset)
		similarity = tf.matmul(valid_embeddings, normalized_embeddings, transpose_b=True)


# Step 5: Begin training.
num_steps = 100001

with tf.Session(graph=graph) as session:
# We must initialize all variables before we use them.
	tf.initialize_all_variables().run()
	print("Initialized")
	
	average_loss = 0
	for step in xrange(num_steps):
		batch_inputs, batch_labels = generate_batch(batch_size, num_skips, skip_window)
		feed_dict = {train_inputs : batch_inputs, train_labels : batch_labels}
		# We perform one update step by evaluating the optimizer op (including it
		# in the list of returned values for session.run()
		_, loss_val = session.run([optimizer, loss], feed_dict=feed_dict)
		average_loss += loss_val
		if step % 2000 == 0:
			if step > 0:
				average_loss /= 2000
			
			# The average loss is an estimate of the loss over the last 2000 batches.
			print("Average loss at step ", step, ": ", average_loss)
			average_loss = 0
			# Note that this is expensive (~20% slowdown if computed every 500 steps)
		if step % 10000 == 0:
			sim = similarity.eval()
			for i in xrange(valid_size):
				#print '---------------------------------'
				#print 'trying to get reverse_dictionary[', valid_examples[i], ']'
				valid_word = reverse_dictionary[valid_examples[i]]
				top_k = 8 # number of nearest neighbors
				nearest = (-sim[i, :]).argsort()[1:top_k+1]
				log_str = "Nearest to %s:" % valid_word
				for k in xrange(top_k):
					close_word = reverse_dictionary[nearest[k]]
					log_str = "%s %s," % (log_str, close_word)
				print(log_str)
	final_embeddings = normalized_embeddings.eval()

# Step 6: Visualize the embeddings.

def plot_with_labels(low_dim_embs, labels, filename='tsne.png'):
	print " Checking: More labels than embedding"
	assert low_dim_embs.shape[0] >= len(labels), "More labels than embeddings"
	print 'ferdi'

	plt.figure(figsize=(18, 18))  #in inches
	for i, label in enumerate(labels):
		x, y = low_dim_embs[i,:]
		plt.scatter(x, y)
		plt.annotate(label,xy=(x, y),xytext=(5, 2),textcoords='offset points',ha='right',va='bottom')

	plt.savefig(filename)

try:
	print "BEFORE SKLEARN"
	from sklearn.manifold import TSNE
	import matplotlib.pyplot as plt

	print "AFTER"

	tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
	plot_only = 500
	low_dim_embs = tsne.fit_transform(final_embeddings[:plot_only,:])
	print "BEFORE LABELS"
	labels = [reverse_dictionary[i] for i in xrange(plot_only)]
	print "START PLOT"
	plot_with_labels(low_dim_embs, labels)

except ImportError:
	print("Please install sklearn and matplotlib to visualize embeddings.")
"""
# Train model
"""for inputs, labels in generate_batch(...):
	feed_dict = {training_inputs: inputs, training_labels: labels}
	_, cur_loss = session.run([optimizer, loss], feed_dict=feed_dict)"""





