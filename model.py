import pygame
import numpy as np
import torch
from torch import nn
from torchvision import transforms


class AppleNet(nn.Module):
    def __init__(self, num_classes: int = 2):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class AppleQualityClassifier:
    """Wraps the PyTorch CNN to classify apple surfaces captured from Pygame."""

    def __init__(self, model_path: str, image_size: int = 64, class_names=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model = AppleNet()
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.image_size = checkpoint.get("image_size", image_size)
            self.class_names = checkpoint.get("classes", class_names or ["damaged", "good"])
        else:
            self.model.load_state_dict(checkpoint)
            self.image_size = image_size
            self.class_names = class_names or ["damaged", "good"]
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose(
            [
                transforms.Resize((self.image_size, self.image_size)),
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
            ]
        )

    def _surface_to_image(self, surface: pygame.Surface):
        """Convert a pygame surface to a PIL image-like numpy array."""
        array = pygame.surfarray.array3d(surface)
        array = np.transpose(array, (1, 0, 2))
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for converting surfaces") from exc
        return Image.fromarray(array)

    def classify_surface(self, surface: pygame.Surface):
        """Return label, confidence, and raw probabilities for a surface."""
        data = self._surface_to_image(surface)
        tensor = self.transform(data).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)
            conf, idx = torch.max(probs, dim=1)
            label = self.class_names[idx.item()]
            return label, conf.item(), probs.squeeze(0).cpu().numpy()

