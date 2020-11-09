import copy
import collections
import torch
import torch.nn as nn
import torch.nn.utils.prune as prune
from archs.mnist.mlp import MLP
from util import prune_fixed_amount, get_prune_params, train, create_model

# TEST 1: Test whether prunning creates a mask 
def test1_test_reference():
    model = MLP()
    print(list(model.named_buffers()))
    prune_fixed_amount(model, 150000)
    print(list(model.named_buffers()))
  
    
# TEST 2: Test whether training after pruning modifies the pruned parameters
def test2_test_retrain():
    from DataSource import get_data
    
    model = MLP()
    
    train_loaders, _ = get_data(10, 'MNIST', mode='iid', batch_size=4)
    
    
    # Getting the pruned weight for the middle layer
    train(model, train_loaders[0], 1)
    prune_fixed_amount(model, 150000)
        
    masks = {}
    for name, buffer in model.named_buffers():
        
        # Reverse the mask so that the 1 means un-pruned weights and 0 means 
        # pruned weights
        masks[name[:-5] + '_orig'] = torch.ones_like(buffer) - buffer
    
    # Applying the reversed mask to all of the parameters
    weight_before_retrain = {}
    for name, param in list(model.named_parameters()):
        if name in masks:
            weight_before_retrain[name] = param * masks[name]
    
    # Train 1 epoch
    train(model, train_loaders[0], 1)
    
    # Proving that the un-pruned weights DO change with training
    print('Whether all parameters are equal: ')
    for name, param in list(model.named_parameters()):
        if name in masks:
            before_training = weight_before_retrain[name]
            print(f'Parameter name: "{name}" {torch.all(before_training.eq(param)).item()}')
      
    # Proving that the pruned weights DO NOT change with training
    print('Whether the pruned parameters are equal: ')
    for name, param in list(model.named_parameters()):
        if name in masks:
            before_training = weight_before_retrain[name]
            print(f'Parameter name: "{name}" {torch.all(before_training.eq(param * masks[name])).item()}')

# TEST 3: Test what the appropriate way for averaging weight is:
    
def test3_try_average():
    
    class DummyDataset(torch.utils.data.Dataset):
        def __init__(self, data, labels):
              'Initialization'
              self.labels = labels
              self.data = data
        
        def __len__(self):
              'Denotes the total number of samples'
              return len(self.labels)
        
        def __getitem__(self, index):
              'Generates one sample of data'
              # Load data and get label
              x = self.data[index]
              y = self.labels[index]
        
              return x, y
    
    train_data, train_data2 = torch.rand(1000, 10), torch.rand(1000, 10)
    train_labels1, train_labels2 = torch.randint(0, 2, (1000,)), torch.randint(0, 2, (1000,))
    
    train_dataset1 = DummyDataset(train_data, train_labels1)
    train_dataset2 = DummyDataset(train_data2, train_labels2)
    
    train_loader1 = torch.utils.data.DataLoader(train_dataset1, batch_size=4)
    train_loader2 = torch.utils.data.DataLoader(train_dataset2, batch_size=4)
    
    model1 = nn.Sequential(nn.Linear(10, 2, bias=True))
    model2 = nn.Sequential(nn.Linear(10, 2, bias=True))
    
    prune_fixed_amount(model1, 0)
    prune_fixed_amount(model2, 0)
    
   
    init_state = model1.state_dict()
    
    
    
    train(model1, train_loader1, 1)
    train(model2, train_loader2, 1)
    
    prune_fixed_amount(model1, 7)
    prune_fixed_amount(model2, 7)
    
    
    models = [model1, model2]
    
    avg_weights = average_weights(models)
    
    print(list(model1.named_parameters()))
    print()
    
    
    # avg_weights = {}
    
    # for name, param in model1.named_parameters():
    #     if name.endswith('_orig'):
    #         avg_weights[name] = torch.ones_like(param)
    
    copy_weights(copy.deepcopy(model1), init_state)
    
    
    print('_________________________')
    print("Initial State: ")
    print('_________________________')
    print(init_state)
    
    print('_________________________')
    print("Copied State: ")
    print('_________________________')
    print(model1.state_dict())
    
    
    # # test_input = torch.ones([1,10])
    # # print(model1(test_input))
    
    # print('_________________________')
    # print(model1.state_dict())
    
    
    
    # Conclusion: You need to update the parameters with name ending with 
    # '_orig' instead of the auxillary 'weight' field created during pruning

def test4_multiple_pruning():
    mlp = MLP()
    prune_fixed_amount(mlp, 0)
    prune_fixed_amount(mlp, 7)
    # finalize_pruning(mlp)
    copy.deepcopy(mlp)
    print(list(mlp.named_parameters()))

# Test 5: see if create_model creates the correct model
def test5_create_model():
    
    model = create_model('mnist', 'mlp')
    prune_fixed_amount(model, 0)
    

   
    


# Helper Methods

def average_weights(models):
    with torch.no_grad():
        weights = []
        for model in models:
            weights.append(dict(model.named_parameters()))
        
        avg = copy.deepcopy(weights[0])
        for key in avg.keys():
            for i in range(1, len(weights)):
                avg[key] += weights[i][key]
            avg[key] = torch.div(avg[key], len(weights))
    return avg


def copy_weights(target_model, source_state_dict):

    for name, param in target_model.named_parameters():
        if name in source_state_dict:
            
            param.data.copy_(source_state_dict[name].data)

def gen_state_dict(model):
    new_state_dict = collections.OrderedDict()
    
    for name, param in model.named_parameters():
        if name.endswith('_orig'):
            new_state_dict[name] = torch.zeros_like(param)
            
    return new_state_dict

def count_zero_weights(model):
    layers, num_param = get_prune_params(model)
    num_zeros = 0
    for layer, _ in layers:
        num_zeros += torch.sum(layer.weight == 0.0)
    return num_zeros

def finalize_pruning(model):
    layers, num_param = get_prune_params(model)
    for layer, _ in layers:
        prune.remove(layer, 'weight')
    

if __name__ == '__main__':
   
    
    
    
    # test1_test_reference()
    
    # test2_test_retrain()
    
    # test3_try_average()
    
    # test4_multiple_pruning()
    
    test5_create_model()
    
    
    # mlp = nn.RNN(10, 20, 2)
    # prune_fixed_amount(mlp, 700)
    
    # # TEST 3: Dummy example
    
    
    
    # # TEST 4: Test on more unusual modules
   
    # mlp = MLP()
    # prune_fixed_amount(mlp, 150000)
    # print(mlp.state_dict().keys())
    
    # rnn = nn.RNN(10, 20, 2)
    # print(get_prune_params(rnn))
    # prune_fixed_amount(rnn, 400)
    # print(list(rnn.named_parameters()))
    
    # for name, weight in rnn.named_parameters():
    #     print(name)
  
            
    