import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter
from torch import nn
from torch.utils.data import DataLoader, Dataset

from model import AppleNet


PROJECT_DIR = Path(__file__).parent
MODEL_PATH = PROJECT_DIR / "models" / "apple_cnn.pth"


class SyntheticAppleDataset(Dataset):
    def __init__(self, size: int = 500, image_size: int = 64):
        self.size = size
        self.image_size = image_size
        self.classes = ["damaged", "good"]
        self.samples = [self._generate_sample() for _ in range(size)]

    def _generate_sample(self):
        label = random.choice(self.classes)
        img = Image.new("RGB", (self.image_size, self.image_size), (20, 70, 20))
        draw = ImageDraw.Draw(img)

        center = (self.image_size // 2 + random.randint(-4, 4), self.image_size // 2 + random.randint(-4, 4))
        radius = random.randint(self.image_size // 3, self.image_size // 2 - 2)
        bbox = [
            center[0] - radius,
            center[1] - radius,
            center[0] + radius,
            center[1] + radius,
        ]

        base_color = (200 + random.randint(-20, 20), 30 + random.randint(-10, 10), 30 + random.randint(-10, 10))
        draw.ellipse(bbox, fill=base_color, outline=(120, 0, 0), width=2)

        # leaf
        leaf_start = (center[0], bbox[1] - 6)
        leaf_end = (leaf_start[0] + random.randint(5, 10), leaf_start[1] - random.randint(5, 10))
        draw.line([leaf_start, leaf_end], fill=(30, 120, 30), width=3)

        noise = Image.effect_noise((self.image_size, self.image_size), random.randint(5, 20))
        img = Image.blend(img, noise.convert("RGB"), 0.08)

        if label == "damaged":
            for _ in range(random.randint(1, 3)):
                patch_radius = random.randint(radius // 4, radius // 3)
                patch_center = (
                    center[0] + random.randint(-radius // 2, radius // 2),
                    center[1] + random.randint(-radius // 2, radius // 2),
                )
                patch_box = [
                    patch_center[0] - patch_radius,
                    patch_center[1] - patch_radius,
                    patch_center[0] + patch_radius,
                    patch_center[1] + patch_radius,
                ]
                draw.ellipse(patch_box, fill=(120, 70, 20))

            img = img.filter(ImageFilter.GaussianBlur(0.8))

        np_img = np.asarray(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(np_img).permute(2, 0, 1)
        tensor = (tensor - 0.5) / 0.5

        target = torch.tensor(self.classes.index(label))
        return tensor, target

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def train():
    torch.manual_seed(42)
    dataset = SyntheticAppleDataset(size=800)
    train_size = int(len(dataset) * 0.8)
    val_size = len(dataset) - train_size
    train_ds, val_ds = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AppleNet().to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    best_val = 0.0
    for epoch in range(8):
        model.train()
        running_loss = 0.0
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * inputs.size(0)

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                logits = model(inputs)
                preds = logits.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.size(0)
        val_acc = correct / total
        print(f"Epoch {epoch+1}: loss={running_loss/train_size:.4f}, val_acc={val_acc:.3f}")
        best_val = max(best_val, val_acc)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "classes": dataset.classes,
            "image_size": dataset.image_size,
            "val_acc": best_val,
        },
        MODEL_PATH,
    )
    print(f"Model saved to {MODEL_PATH.resolve()}")


if __name__ == "__main__":
    train()


