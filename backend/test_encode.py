import torch
from sentence_transformers import SentenceTransformer
import sys

print('Loading model...')
try:
    model = SentenceTransformer('cl-nagoya/ruri-v3-310m')
    print('Model loaded. Encoding...')
    res = model.encode(['test'], convert_to_tensor=True, device='cuda' if torch.cuda.is_available() else 'cpu')
    print('Done encoding!')
except Exception as e:
    print('Error:', e)
    sys.exit(1)
print('Script finished.')
