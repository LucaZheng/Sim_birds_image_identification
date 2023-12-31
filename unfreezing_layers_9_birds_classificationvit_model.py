# -*- coding: utf-8 -*-
"""Unfreezing layers-9 birds classificationvit_model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1VlmKFbqbENVbisr-3BDWZ-YAcggy6f00

# Connect Gdrive

---
"""

# unzip images and reate image folders on drive
!cd /content
!unzip /content/drive/MyDrive/datasets/birds/cropped_petrel.zip
# Define paths
DATASET_PATH ="/content/cropped_petrel/"

# Commented out IPython magic to ensure Python compatibility.
# %%time
# import glob
# dataset_images = glob.glob(f"{DATASET_PATH}**/*.jpg")
# # Get dataset size
# total = len(dataset_images)
# 
# # View samples counts
# print(f'TOTAL: {total}')

"""# Load Libarary

---



---


"""

# System libraries
from pathlib import Path
import os.path
import random
import time
import glob
import copy
import time
import tensorflow.keras.callbacks as cb
import json

# Utilities
import pandas as pd, numpy as np
import seaborn as sns

# Sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report,confusion_matrix
from sklearn.metrics import roc_curve, precision_recall_curve, auc
from sklearn.metrics import precision_recall_curve,average_precision_score,roc_auc_score, accuracy_score
from sklearn.preprocessing import label_binarize
from sklearn.utils import class_weight
from sklearn.preprocessing import LabelEncoder
import matplotlib.colors as mcolors

# Tensorflow Libraries
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Model
from tensorflow.keras import layers,models,Sequential
from keras.preprocessing.image import ImageDataGenerator
from keras.layers import Dense, Dropout, BatchNormalization, Flatten, GlobalAveragePooling2D, GlobalMaxPooling2D
from tensorflow.keras.callbacks import Callback, EarlyStopping,ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import Model
from tensorflow.keras.layers.experimental import preprocessing
from tensorflow.keras import regularizers
import tensorflow_hub as hub

# Visualization Libraries
import matplotlib.cm as cm
import cv2
import seaborn as sns
import matplotlib.pyplot as plt

!wget https://raw.githubusercontent.com/LucaZheng/DLFunction/main/modifiedhelpers.py
from modifiedhelpers import generate_labels, build_df, _load, encode_labels, create_pipeline, train_model

# add-in function block

# Concat pretrained + fc
def create_model(pretrained_model, model_name):
    initializer = tf.keras.initializers.GlorotNormal(seed=CFG.SEED)

    model_sequential = Sequential([
        layers.Input(shape=CFG.IMAGE_SIZE, dtype=tf.float32, name='input_image'),
        pretrained_model,
        layers.Dropout(0.2),
        layers.Dense(512, activation='relu', kernel_initializer=initializer),
        layers.Dense(256, activation='relu', kernel_initializer=initializer),
        layers.Dense(24, dtype=tf.float32, activation='softmax', kernel_initializer=initializer)
    ], name=model_name)

    return model_sequential

def compile_model(model):
    # Compile the model
    model.compile(
        loss=tf.keras.losses.CategoricalCrossentropy(),
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        metrics=METRICS
    )

def train_model(model, epochs, callbacks, train_ds, val_ds):
    # Train the model
    print(f'Training {model.name}.')
    print(f'Train on {len(train_df)} samples, validate on {len(val_df)} samples.')
    print('----------------------------------')

    history = model.fit(
        train_ds,
        epochs=epochs,
        callbacks=callbacks,
        validation_data=val_ds
    )

    return history

import numpy as np
import matplotlib.pyplot as plt

# plotting function
# create a list of colors without red ones
colors = ['tab:blue', 'tab:green', 'tab:purple', 'tab:brown']
# Assuming histories is a list of History objects and model_names is a list of the corresponding model names
def plot_history(histories, model_names, metric='val_loss', highlight=None):
    plt.figure(figsize=(10,6))

    for i, (history, model_name) in enumerate(zip(histories, model_names)):
        # get only the validation loss
        # change from history.history[metric] to down blow
        metric_values = history[metric]

        if model_name == highlight:
            # Highlight this model with thicker, dashed red line
            plt.plot(metric_values, 'r--', linewidth=2.5, label=model_name)
        else:
            # use colors from the colors list
            plt.plot(metric_values, color=colors[i % len(colors)], label=model_name)

    plt.xlabel('Epochs')
    plt.ylabel(metric)
    plt.title(f'{metric.capitalize()} vs. Epochs for No. Unfreezed Layers')
    plt.legend()
    plt.grid(True)
    plt.show()

def float32_and_ndarray_to_float(data):
    if isinstance(data, dict):
        return {k: float32_and_ndarray_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [float32_and_ndarray_to_float(v) for v in data]
    elif isinstance(data, np.float32):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

"""# One-hot lables and create DF"""

class CFG:
    EPOCHS = 30
    BATCH_SIZES = 50
    SEED = 42
    TF_SEED = 768
    HEIGHT = 224
    WIDTH = 224
    CHANNELS = 3
    IMAGE_SIZE = (224, 224, 3)

# Build the Dataset DataFrame
dataset_df = build_df(dataset_images, generate_labels(dataset_images), seed=CFG.SEED)

# Label encoder
# Generate Label Encoder
label_encoder = LabelEncoder()

# Label Encode the Image Labels
dataset_df['label_encoded'] = label_encoder.fit_transform(dataset_df.label)

# View first 10 samples
dataset_df.head(10)

dataset_df.label.value_counts()

"""# Train test split"""

# Create Train/Test split with Training Set
train_split_idx, val_test_split_idx, _, _ = train_test_split(dataset_df.index,
                                                        dataset_df.label_encoded,
                                                        test_size=0.3,
                                                        stratify=dataset_df.label_encoded,
                                                        random_state=CFG.SEED)

# Get training and validation data
train_df = dataset_df.iloc[train_split_idx].reset_index(drop=True)
val_test_df = dataset_df.iloc[val_test_split_idx].reset_index(drop=True)

# Create Train/Test split with Training Set
val_split_idx, test_split_idx, _, _ = train_test_split(val_test_df.index,
                                                       val_test_df.label_encoded,
                                                       test_size=0.6,
                                                       stratify=val_test_df.label_encoded,
                                                       random_state=CFG.SEED)

# Get validation and test data
val_df = dataset_df.iloc[val_split_idx].reset_index(drop=True)
test_df = dataset_df.iloc[test_split_idx].reset_index(drop=True)

"""# Augmentation"""

# Build augmentation layer
augmentation_layer = Sequential([
    layers.RandomFlip(mode='horizontal_and_vertical', seed=CFG.TF_SEED),
    layers.RandomZoom(height_factor=(-0.1, 0.1), width_factor=(-0.1, 0.1), seed=CFG.TF_SEED),
], name='augmentation_layer')

"""# Define Training strategies"""

# Define Early Stopping Callback
early_stopping_callback = tf.keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=3,
    restore_best_weights=True)

# Define Reduce Learning Rate Callback
reduce_lr_callback = tf.keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss',
    patience=2,
    factor=0.1,
    verbose=1)

# Define Callbacks and Metrics lists
CALLBACKS = [early_stopping_callback, reduce_lr_callback]
METRICS = ['accuracy']
tf.random.set_seed(CFG.SEED)

"""# EfficientNetB2V2"""

eff_preprocess = tf.keras.applications.efficientnet.preprocess_input

# Generate Train Input Pipeline
eff_train_ds = create_pipeline(train_df, _load, preprocess_function=eff_preprocess,
                           height=CFG.HEIGHT, width=CFG.WIDTH,
                           augment_layer=augmentation_layer,
                           augment=True,
                           batch_size=CFG.BATCH_SIZES,
                           if_vt = False,
                           shuffle=False, prefetch=True)

# Generate Validation Input Pipeline
eff_val_ds = create_pipeline(val_df, _load, preprocess_function=eff_preprocess,
                         height=CFG.HEIGHT, width=CFG.WIDTH,
                         augment_layer=None,
                         augment=False,
                         if_vt = False,
                         batch_size=CFG.BATCH_SIZES,
                         shuffle=False, prefetch=False)

# Generate Test Input Pipeline
eff_test_ds = create_pipeline(test_df, _load, preprocess_function=eff_preprocess,
                          height=CFG.HEIGHT, width=CFG.WIDTH,
                          augment_layer=None,
                          augment=False,
                          if_vt = False,
                          batch_size=CFG.BATCH_SIZES,
                          shuffle=False, prefetch=False)

# View string representation of datasets
print('========================================')
print('Train Input Data Pipeline:\n\n', eff_train_ds)
print('========================================')
print('Validation Input Data Pipeline:\n\n', eff_val_ds)
print('========================================')
print('Test Input Data Pipeline:\n\n', eff_test_ds)
print('========================================')

# download models and create a list of the same model
eff_pretrained_models = []

for i in range(6):
  model = tf.keras.applications.EfficientNetV2B2(
  input_shape=(224, 224, 3),
  include_top=False,
  weights='imagenet',
  pooling='max'
  )

  for layer in model.layers:
      layer.trainable = False

  eff_pretrained_models.append(model)

eff_pretrained_models[0].summary()

# Create pretrained models for concat (only pre-trained)
eff_pretrained0=eff_pretrained_models[0]
eff_pretrained1=eff_pretrained_models[1]
eff_pretrained2=eff_pretrained_models[2]
eff_pretrained3=eff_pretrained_models[3]
eff_pretrained4=eff_pretrained_models[4]
eff_pretrained5=eff_pretrained_models[5]

eff_blocks_to_unfreeze = [
[],
['top_'],
['top_', 'block6'],
['top_', 'block6', 'block5'],
['top_', 'block6', 'block5', 'block4'],
['top_', 'block6', 'block5', 'block4','block3']
]

# setting layers for unfreezing
eff_pretrained_list = [eff_pretrained0, eff_pretrained1, eff_pretrained2, eff_pretrained3, eff_pretrained4, eff_pretrained5]

for i, dense_pretrained in enumerate(eff_pretrained_list):
  for layer in dense_pretrained.layers:
    if any(block in layer.name for block in eff_blocks_to_unfreeze[i]) and 'bn' not in layer.name:
      layer.trainable = True

# Generate concated Model (pretrain+fc)
eff_unfreeze0 = create_model(eff_pretrained0,model_name='base_eff')
eff_unfreeze1 = create_model(eff_pretrained1,model_name='train_b7')
eff_unfreeze2 = create_model(eff_pretrained2,model_name='train_b6_7')
eff_unfreeze3 = create_model(eff_pretrained3,model_name='train_b5_7')
eff_unfreeze4 = create_model(eff_pretrained4,model_name='train_b4_7')
eff_unfreeze5 = create_model(eff_pretrained5,model_name='train_b3_7')

# Complie for training
compile_model(eff_unfreeze0)
compile_model(eff_unfreeze1)
compile_model(eff_unfreeze2)
compile_model(eff_unfreeze3)
compile_model(eff_unfreeze4)
compile_model(eff_unfreeze5)

# Check if desired layers were unfrozen
def print_layer_info(model, prefix=""):
    for i, layer in enumerate(model.layers):
        print(prefix + str(i), layer.name, layer.trainable)
        if isinstance(layer, tf.keras.Model):
            print_layer_info(layer, prefix + str(i) + "_")

print_layer_info(eff_unfreeze5)

"""## Train EfficientNet model"""

eff_models = [eff_unfreeze0,eff_unfreeze1,eff_unfreeze2,eff_unfreeze3,eff_unfreeze4,eff_unfreeze5]
eff_histories = []
eff_training_times = []

for model in eff_models:  # assuming `models` is a list of your models
    start_time = time.time()

    history = train_model(model, 100, CALLBACKS, eff_train_ds, eff_val_ds)

    end_time = time.time()
    training_time = end_time - start_time

    eff_histories.append(history)
    eff_training_times.append(training_time)

eff_training_times[:4]

# Predict test dataset
eff_probs = []
eff_accs = []

for model in eff_models[:4]:
    # prediction
    predictions = model.predict(eff_test_ds)
    # append
    eff_probs.append(predictions)

# Separate labels from dense_test_ds
y_true = np.concatenate([y for x, y in eff_test_ds], axis=0)
y_true = np.argmax(y_true, axis=-1)

for preds in eff_probs:
    # Get predicted classes from probabilities
    y_pred = np.argmax(preds, axis=-1)

    # Calculate accuracy
    accuracy = accuracy_score(y_true, y_pred)

    # Append
    eff_accs.append(accuracy)

eff_accs

# loss visualization
plot_history(loaded_eff_history_dicts[:4], ['base_eff', 'train_b7', 'train_b6_7','train_b5_7'], 'loss', highlight='base_eff')

# train visualization
plot_history(loaded_eff_history_dicts[:4], ['base_eff', 'train_b7', 'train_b6_7','train_b5_7'], 'accuracy', highlight='base_eff')

# validation visualization
plot_history(loaded_eff_history_dicts[:4], ['base_eff', 'train_b7', 'train_b6_7','train_b5_7'], 'val_accuracy', highlight='base_eff')

from google.colab import drive
drive.mount('/content/drive')

# Define the model names
eff_model_names = ['base_eff', 'train_b7', 'train_b6_7','train_b5_7']

plt.figure(figsize=(10, 6))

# Create a bar chart
plt.bar(eff_model_names, eff_accs, color='blue', alpha=0.7)

# Add title and axis names
plt.title('Test Accuracies')
plt.ylim(0.75)
plt.xlabel('Experiment Notations')
plt.ylabel('Test Accuracy')

# Show the plot
plt.show()

eff_history_dicts = [float32_and_ndarray_to_float(history.history) for history in eff_histories]
eff_probs = float32_and_ndarray_to_float(eff_probs)

# Saving histories
with open('/content/drive/MyDrive/datasets/birds/histories/'+'eff_histories.json', 'w') as f:
    json.dump(eff_history_dicts, f)
with open('/content/drive/MyDrive/datasets/birds/histories/'+'eff_prob.json', 'w') as f:
    json.dump(eff_probs, f)

with open('/content/drive/MyDrive/datasets/birds/histories/'+'dense_histories.json', 'r') as f:
    loaded_dense_history_dicts = json.load(f)
    loaded_dense_history_dicts = loaded_dense_history_dicts[:4]

base_eff = loaded_dense_history_dicts[0]
train_b7 = loaded_dense_history_dicts[1]
train_b6_7 = loaded_dense_history_dicts[2]
train_b5_7 = loaded_dense_history_dicts[3]

model_names = ['Base_Resmodel','Unfreeze_L5','Unfreeze_L45','Unfreeze_L345']

# loss visualization
plot_history(loaded_dense_history_dicts, ['Base_Resmodel','Unfreeze_L5','Unfreeze_L45','Unfreeze_L345'], highlight='Base_Resmodel')

def plot_history(histories, model_names, highlight=None):
    plt.figure(figsize=(10,6))

    for i, (history, model_name) in enumerate(zip(histories, model_names)):
        # get only the validation loss
        metric_values = history['val_loss']

        if model_name == highlight:
            # Highlight this model with thicker, dashed red line
            plt.plot(metric_values, 'r--', linewidth=2.5, label=model_name)
        else:
            # use colors from the colors list
            plt.plot(metric_values, color=colors[i % len(colors)], label=model_name)

    plt.xlabel('Epochs')
    plt.ylabel('val_loss')
    plt.title('Val_loss vs. Epochs for No. Unfreezed Layers')
    plt.legend()
    plt.grid(True)
    plt.show()

"""# DenseNet"""

dense_preprocess = tf.keras.applications.densenet.preprocess_input

# Generate Train Input Pipeline
dense_train_ds = create_pipeline(train_df, _load, preprocess_function=dense_preprocess,
                           height=CFG.HEIGHT, width=CFG.WIDTH,
                           augment_layer=augmentation_layer,
                           augment=True,
                           batch_size=CFG.BATCH_SIZES,
                           if_vt = False,
                           shuffle=False, prefetch=True)

# Generate Validation Input Pipeline
dense_val_ds = create_pipeline(val_df, _load, preprocess_function=dense_preprocess,
                         height=CFG.HEIGHT, width=CFG.WIDTH,
                         augment_layer=None,
                         augment=False,
                         if_vt = False,
                         batch_size=CFG.BATCH_SIZES,
                         shuffle=False, prefetch=False)

# Generate Test Input Pipeline
dense_test_ds = create_pipeline(test_df, _load, preprocess_function=dense_preprocess,
                          height=CFG.HEIGHT, width=CFG.WIDTH,
                          augment_layer=None,
                          augment=False,
                          if_vt = False,
                          batch_size=CFG.BATCH_SIZES,
                          shuffle=False, prefetch=False)

# View string representation of datasets
print('========================================')
print('Train Input Data Pipeline:\n\n', dense_train_ds)
print('========================================')
print('Validation Input Data Pipeline:\n\n', dense_val_ds)
print('========================================')
print('Test Input Data Pipeline:\n\n', dense_test_ds)
print('========================================')

pretrained_models = []

for i in range(5):
  model = tf.keras.applications.DenseNet201(
  input_shape=(224, 224, 3),
  include_top=False,
  weights='imagenet',
  pooling='max'
  )

  for layer in model.layers:
      layer.trainable = False

  pretrained_models.append(model)

# Create pretrained models for concat (only pre-trained)
dense_pretrained0=pretrained_models[0]
dense_pretrained1=pretrained_models[1]
dense_pretrained2=pretrained_models[2]
dense_pretrained3=pretrained_models[3]
dense_pretrained4=pretrained_models[4]

dense_blocks_to_unfreeze = [
[],
['conv5_'],
['conv5_', 'conv4_'],
['conv5_', 'conv4_', 'conv3_'],
['conv5_', 'conv4_', 'conv3_', 'conv2_']
]

# setting layers for unfreezing
dense_pretrained_list = [dense_pretrained0, dense_pretrained1, dense_pretrained2, dense_pretrained3, dense_pretrained4]

for i, dense_pretrained in enumerate(dense_pretrained_list):
  for layer in dense_pretrained.layers:
    if any(block in layer.name for block in dense_blocks_to_unfreeze[i]) and 'bn' not in layer.name:
      layer.trainable = True

# Generate concated Model (pretrain+fc)
dense201_unfreeze0 = create_model(dense_pretrained0,model_name='base')
dense201_unfreeze1 = create_model(dense_pretrained1,model_name='train_L5')
dense201_unfreeze2 = create_model(dense_pretrained2,model_name='train_L45')
dense201_unfreeze3 = create_model(dense_pretrained3,model_name='train_L345')
dense201_unfreeze4 = create_model(dense_pretrained4,model_name='train_L2345')

# Complie for training
compile_model(dense201_unfreeze0)
compile_model(dense201_unfreeze1)
compile_model(dense201_unfreeze2)
compile_model(dense201_unfreeze3)
compile_model(dense201_unfreeze4)

# Check if desired layers were unfrozen
def print_layer_info(model, prefix=""):
    for i, layer in enumerate(model.layers):
        print(prefix + str(i), layer.name, layer.trainable)
        if isinstance(layer, tf.keras.Model):
            print_layer_info(layer, prefix + str(i) + "_")

print_layer_info(dense201_unfreeze4)

"""## Train DenseNet201"""

dense_models = [dense201_unfreeze0,dense201_unfreeze1,dense201_unfreeze2,dense201_unfreeze3,dense201_unfreeze4]
dense_histories = []
dense_training_times = []

for model in dense_models:  # assuming `models` is a list of your models
    start_time = time.time()

    history = train_model(model, 100, CALLBACKS, dense_train_ds, dense_val_ds)

    end_time = time.time()
    training_time = end_time - start_time

    dense_histories.append(history)
    dense_training_times.append(training_time)

# Predict test dataset
dense_probs = []
#dense_accs = []

for model in dense_models[:-1]:
    # prediction
    predictions = model.predict(dense_test_ds)
    # append
    dense_probs.append(predictions)

#for preds in dense_accs:
    # Get predicted classes
    #y_pred = np.argmax(preds, axis=-1)

    # Calculate accuracy
    #accuracy = accuracy_score(dense_test_ds, y_pred)

    # append
    #dense_accs.append(accuracy)

dense_training_times[:-1]

# loss visualization
plot_history(dense_histories[:-1], ['Base_Resmodel', 'Unfreeze_L5', 'Unfreeze_L45','Unfreeze_L345'], 'loss', highlight='Base_Resmodel')

# train visualization
plot_history(dense_histories[:-1], ['Base_Resmodel', 'Unfreeze_L5', 'Unfreeze_L45','Unfreeze_L345'], 'accuracy', highlight='Base_Resmodel')

# validation visualization
plot_history(dense_histories[:-1], ['Base_Resmodel', 'Unfreeze_L5', 'Unfreeze_L45','Unfreeze_L345'], 'val_accuracy', highlight='Base_Resmodel')

def float32_and_ndarray_to_float(data):
    if isinstance(data, dict):
        return {k: float32_and_ndarray_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [float32_and_ndarray_to_float(v) for v in data]
    elif isinstance(data, np.float32):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

dense_history_dicts = [float32_and_ndarray_to_float(history.history) for history in dense_histories]
dense_probs = float32_and_ndarray_to_float(dense_probs)

# Saving histories
with open('/content/drive/MyDrive/datasets/birds/histories/'+'dense_histories.json', 'w') as f:
    json.dump(dense_history_dicts, f)
with open('/content/drive/MyDrive/datasets/birds/histories/'+'dense_prob.json', 'w') as f:
    json.dump(dense_probs, f)

with open('/content/drive/MyDrive/datasets/birds/histories/'+'dense_histories.json', 'r') as f:
    loaded_dense_history_dicts = json.load(f)

with open('/content/drive/MyDrive/datasets/birds/histories/'+'dense_prob.json', 'r') as f:
    loaded_dense_probs = json.load(f)

dense_accs = []

# Separate labels from dense_test_ds
y_true = np.concatenate([y for x, y in dense_test_ds], axis=0)
y_true = np.argmax(y_true, axis=-1)

for preds in loaded_dense_probs:
    # Get predicted classes from probabilities
    y_pred = np.argmax(preds, axis=-1)

    # Calculate accuracy
    accuracy = accuracy_score(y_true, y_pred)

    # Append
    dense_accs.append(accuracy)

# Define the model names
model_names = ['Base_model', 'Unfreeze_L5', 'Unfreeze_L45','UNfreeze_L345']

plt.figure(figsize=(10, 6))

# Create a bar chart
plt.bar(model_names, dense_accs, color='blue', alpha=0.7)

# Add title and axis names
plt.title('Test Accuracies')
plt.ylim(0.75)
plt.xlabel('Experiment Notations')
plt.ylabel('Test Accuracy')

# Show the plot
plt.show()

"""# Vision Transformer"""

!pip install -q vit-keras
!pip install tensorflow_addons

# Generate Train Input Pipeline
vt_train_ds = create_pipeline(train_df, _load, preprocess_function=None,
                           height=CFG.HEIGHT, width=CFG.WIDTH,
                           augment_layer=augmentation_layer,
                           augment=True,
                           batch_size=CFG.BATCH_SIZES,
                           if_vt = True,
                           shuffle=False, prefetch=True)

# Generate Validation Input Pipeline
vt_val_ds = create_pipeline(val_df, _load, preprocess_function=None,
                         height=CFG.HEIGHT, width=CFG.WIDTH,
                         augment_layer=None,
                         augment=False,
                         if_vt = True,
                         batch_size=CFG.BATCH_SIZES,
                         shuffle=False, prefetch=False)

# Generate Test Input Pipeline
vt_test_ds = create_pipeline(test_df, _load, preprocess_function=None,
                          height=CFG.HEIGHT, width=CFG.WIDTH,
                          augment_layer=None,
                          augment=False,
                          if_vt = True,
                          batch_size=CFG.BATCH_SIZES,
                          shuffle=False, prefetch=False)

# View string representation of datasets
print('========================================')
print('Train Input Data Pipeline:\n\n', vt_train_ds)
print('========================================')
print('Validation Input Data Pipeline:\n\n', vt_val_ds)
print('========================================')
print('Test Input Data Pipeline:\n\n', vt_test_ds)
print('========================================')

# download models and create a list of the same model
from vit_keras import vit
vit_pretrained_models = []

for i in range(6):
  model = vit.vit_b16(
  image_size=224,
  activation='softmax',
  pretrained=True,
  include_top=False,
  pretrained_top=False,
  classes=9)

  for layer in model.layers:
      layer.trainable = False

  vit_pretrained_models.append(model)

vit_pretrained_models[0].summary()

# Create pretrained models for concat (only pre-trained)
vit_pretrained0=vit_pretrained_models[0]
vit_pretrained1=vit_pretrained_models[1]
vit_pretrained2=vit_pretrained_models[2]
vit_pretrained3=vit_pretrained_models[3]
vit_pretrained4=vit_pretrained_models[4]
vit_pretrained5=vit_pretrained_models[5]

vit_blocks_to_unfreeze = [
[],
['encoderblock_11'],
['encoderblock_11', 'encoderblock_10', 'encoderblock_9'],
['encoderblock_11', 'encoderblock_10', 'encoderblock_9', 'encoderblock_8','encoderblock_7'],
['encoderblock_11', 'encoderblock_10', 'encoderblock_9', 'encoderblock_8','encoderblock_7','encoderblock_6','encoderblock_5']
]

# setting layers for unfreezing
vit_pretrained_list = [vit_pretrained0, vit_pretrained1,
                       vit_pretrained2, vit_pretrained3,
                       vit_pretrained4]

for i, vit_pretrained in enumerate(vit_pretrained_list):
  for layer in vit_pretrained.layers:
    if any(block in layer.name for block in vit_blocks_to_unfreeze[i]):
      layer.trainable = True

for layer in vit_pretrained5.layers:
      layer.trainable = True

# Generate concated Model (pretrain+fc)
vit_unfreeze0 = create_model(vit_pretrained0,model_name='base_eff')
vit_unfreeze1 = create_model(vit_pretrained1,model_name='train_b11')
vit_unfreeze2 = create_model(vit_pretrained2,model_name='train_b9_11')
vit_unfreeze3 = create_model(vit_pretrained3,model_name='train_b7_11')
vit_unfreeze4 = create_model(vit_pretrained4,model_name='train_b5_11')
vit_unfreeze5 = create_model(vit_pretrained5,model_name='train_all')

# Complie for training
compile_model(vit_unfreeze0)
compile_model(vit_unfreeze1)
compile_model(vit_unfreeze2)
compile_model(vit_unfreeze3)
compile_model(vit_unfreeze4)
compile_model(vit_unfreeze5)

"""##### seperate training"""

from vit_keras import vit
vit_pretrained5 = vit.vit_b16(
  image_size=224,
  activation='softmax',
  pretrained=True,
  include_top=False,
  pretrained_top=False,
  classes=9)

for layer in vit_pretrained5.layers:
      layer.trainable = True

vit_unfreeze5 = create_model(vit_pretrained5,model_name='train_all')
compile_model(vit_unfreeze5)

start_time = time.time()

train_all_history = train_model(vit_unfreeze5, 100, CALLBACKS, vt_train_ds, vt_val_ds)

end_time = time.time()
training_time = end_time - start_time

training_time

predictions = vit_unfreeze5.predict(vt_test_ds)

# Separate labels from dense_test_ds
y_true = np.concatenate([y for x, y in vt_test_ds], axis=0)
y_true = np.argmax(y_true, axis=-1)


# Get predicted classes from probabilities
y_pred = np.argmax(predictions, axis=-1)

# Calculate accuracy
accuracy = accuracy_score(y_true, y_pred)

accuracy

"""## Train ViT"""

vit_models = [vit_unfreeze0,vit_unfreeze1,
              vit_unfreeze2,vit_unfreeze3,
              vit_unfreeze4,vit_unfreeze5]
vit_histories = []
vit_training_times = []

for model in vit_models:  # assuming `models` is a list of your models
    start_time = time.time()

    history = train_model(model, 100, CALLBACKS, vt_train_ds, vt_val_ds)

    end_time = time.time()
    training_time = end_time - start_time

    vit_histories.append(history)
    vit_training_times.append(training_time)

vit_training_times

# Predict test dataset
vit_probs = []
vit_accs = []

for model in vit_models[:-1]:
    # prediction
    predictions = model.predict(vt_test_ds)
    # append
    vit_probs.append(predictions)

# Separate labels from dense_test_ds
y_true = np.concatenate([y for x, y in vt_test_ds], axis=0)
y_true = np.argmax(y_true, axis=-1)

for preds in vit_probs:
    # Get predicted classes from probabilities
    y_pred = np.argmax(preds, axis=-1)

    # Calculate accuracy
    accuracy = accuracy_score(y_true, y_pred)

    # Append
    vit_accs.append(accuracy)

vit_accs

# loss visualization
plot_history(vit_histories[:-1], ['base_vit', 'train_b11', 'train_b10_11','train_b9_11','train_b8_11','train_b7_11'], 'val_loss', highlight='base_vit')

# validation visualization
plot_history(vit_histories[:-1], ['base_vit', 'train_b11', 'train_b10_11','train_b9_11','train_b8_11','train_b7_11'], 'val_accuracy', highlight='base_vit')

vit_accs

# Define the model names
vit_model_names = ['base_vit', 'train_b11', 'train_b10_11','train_b9_11','train_b8_11','train_b7_11']

plt.figure(figsize=(10, 6))

# Create a bar chart
plt.bar(vit_model_names, vit_accs, color='blue', alpha=0.7)

# Add title and axis names
plt.title('Test Accuracies')
plt.ylim(0.70)
plt.xlabel('Experiment Notations')
plt.ylabel('Test Accuracy')

# Show the plot
plt.show()

def float32_and_ndarray_to_float(data):
    if isinstance(data, dict):
        return {k: float32_and_ndarray_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [float32_and_ndarray_to_float(v) for v in data]
    elif isinstance(data, np.float32):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

vit_history_dicts = float32_and_ndarray_to_float(train_all_history.history)

# Saving histories
with open('/content/drive/MyDrive/datasets/birds/histories/'+'vit_histories1.json', 'w') as f:
    json.dump(vit_history_dicts, f)

# load all the histories
with open('/content/drive/MyDrive/datasets/birds/histories/vit_histories.json', 'r') as f:
    loaded_vit_history_dicts = json.load(f)

with open('/content/drive/MyDrive/datasets/birds/histories/vit_histories1.json', 'r') as f:
    loaded_vit_history_dicts1 = json.load(f)

loaded_vit_history_dicts.append(loaded_vit_history_dicts1)
len(loaded_vit_history_dicts)

# loss visualization
plot_history(loaded_vit_history_dicts, ['base_vit', 'train_b11', 'train_b7_11','train_b5_11','train_all'], 'val_loss', highlight='base_vit')

# validation visualization
plot_history(loaded_vit_history_dicts, ['base_vit', 'train_b11', 'train_b7_11','train_b5_11','train_all'], 'val_accuracy', highlight='base_vit')

0.731
 0.823
 0.922
 0.948
 0.957

vit_training_time = [1218.2379698753357,
 862.2635505199432,
 732.088536977768,
 658.049325466156,
 769.4463822841644,
 887.8405685424805]

"""# Vit visulization"""

from vit_keras import vit, utils, visualize

def attention_map(model,pic_path):
  # Load a model
  image_size = 224
  classes = utils.get_imagenet_classes()

  # Get an image and compute the attention map
  image = utils.read(pic_path, image_size)
  attention_map = visualize.attention_map(model=model, image=image)
  print('Prediction:', classes[
      model.predict(vit.preprocess_inputs(image)[np.newaxis])[0].argmax()]
  )

  # Plot results
  fig, (ax1, ax2) = plt.subplots(ncols=2)
  ax1.axis('off')
  ax2.axis('off')
  ax1.set_title('Original')
  ax2.set_title('Attention Map')
  _ = ax1.imshow(image)
  _ = ax2.imshow(attention_map)

attention_map(vit_pretrained0,'/content/cropped_petrel/black_winged_petrel/black_winged_petrel_263.jpg')

