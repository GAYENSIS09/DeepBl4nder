"""UE5 Bridge : client REST pour communiquer avec un serveur Unreal Engine 5.

Le bridge envoie des commandes REST à un serveur UE5 qui controle
l'éditeur UE5 en headless (level creation, materials, lighting, MRQ render).
"""

from DeepBl4nder.bridges.ue5.bridge import UE5Bridge

__all__ = ["UE5Bridge"]
