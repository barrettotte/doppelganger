"""Suppress harmless dependency warnings. Import before any third-party packages."""

import warnings

# resemble-perth uses pkg_resources which setuptools deprecated - remove when perth updates
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# diffusers LoRACompatibleLinear deprecation - remove when diffusers drops it
warnings.filterwarnings("ignore", message=".*LoRACompatibleLinear.*", category=FutureWarning)

# torch sdp_kernel deprecation - remove when chatterbox switches to sdpa_kernel
warnings.filterwarnings("ignore", message=".*sdp_kernel.*", category=FutureWarning)

# transformers past_key_values tuple deprecation - remove when chatterbox updates
warnings.filterwarnings("ignore", message=".*past_key_values.*as a tuple of tuples.*", category=UserWarning)
