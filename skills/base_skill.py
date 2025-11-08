# -*- coding: utf-8 -*-
"""
Base Skill Class for SEBAS Skills System
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging


class BaseSkill(ABC):
    """
    Abstract base class for all SEBAS skills.

    Skills are modular plugins that handle specific intents and commands.
    Each skill should implement the core methods defined here.
    """

    def __init__(self, assistant_ref):
        """
        Initialize the skill with a reference to the main assistant.

        Args:
            assistant_ref: Reference to the main Sebas assistant instance
        """
        self.assistant = assistant_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = True

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """
        Check if this skill can handle the given intent.

        Args:
            intent: The intent name to check

        Returns:
            bool: True if this skill can handle the intent
        """
        pass

    @abstractmethod
    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        """
        Handle the given intent with provided slots.

        Args:
            intent: The intent name to handle
            slots: Dictionary of slot values extracted from the command

        Returns:
            bool: True if the intent was handled successfully
        """
        pass

    @abstractmethod
    def get_intents(self) -> List[str]:
        """
        Return a list of intents this skill can handle.

        Returns:
            List[str]: List of intent names
        """
        pass

    def get_description(self) -> str:
        """
        Get a human-readable description of what this skill does.
        Override in subclasses for better descriptions.

        Returns:
            str: Description of the skill
        """
        return f"{self.__class__.__name__} - handles {', '.join(self.get_intents())}"

    def is_enabled(self) -> bool:
        """
        Check if this skill is currently enabled.

        Returns:
            bool: True if the skill is enabled
        """
        return self.enabled

    def set_enabled(self, enabled: bool):
        """
        Enable or disable this skill.

        Args:
            enabled: Whether to enable the skill
        """
        self.enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.logger.info(f"Skill {self.__class__.__name__} {status}")