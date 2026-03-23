import winsound
import threading
import os
import sys # Added sys for _MEIPASS checks
from typing import Optional, Dict
from pathlib import Path


class SoundManager:
    """
    Gerenciador de áudio que suporta tanto arquivos WAV/MP3 quanto sons procedurais.
    
    Features:
    - Carrega automaticamente arquivos de áudio da pasta assets/sounds/
    - Fallback para sons procedurais se arquivos não existirem
    - Execução assíncrona (não trava a UI)
    - Volume controlável
    """
    
    
    def __init__(self, sound_path: str = "assets/sounds/", enabled: bool = True):
        """
        Inicializa o gerenciador de som.
        Tenta usar pygame.mixer para áudio avançado (volume, mixagem).
        Cai para winsound se pygame não estiver disponível.
        """
        self._enabled = enabled
        self._pygame_available = False
        self._volume = 0.5  # Volume padrão (0.0 a 1.0)
        
        try:
            # Hide Pygame support prompt gracefully
            os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._pygame_available = True
                
            if self._pygame_available:
                print("🔊 Sistema de Áudio: Pygame Mixer (Alta Qualidade)")
        except ImportError:
            print("🔊 Sistema de Áudio: Winsound (Fallback - Sem controle de volume)")
            print("💡 Dica: Instale 'pygame' para melhor qualidade de áudio.")
        except Exception as e:
            print(f"⚠️ Erro ao iniciar Pygame: {e}")
            print("🔊 Sistema de Áudio: Winsound (Fallback)")

        if enabled:
            # Tentar resolver caminho absoluto para assets
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            path_obj = Path(sound_path)
            if not path_obj.is_absolute():
                self.sound_path = Path(base_path) / sound_path
            else:
                self.sound_path = path_obj
        else:
            self.sound_path = Path(sound_path)
            
        # Cache de sons (Pygame Sounds ou Paths para Winsound)
        self._sounds = {}
        
        # Fallback: Presets de sons procedurais (beeps)
        self._fallback_beeps: Dict[str, list] = {
            'mana_gain': [(800, 100), (1000, 150)],
            'mana_loss': [(400, 200)],
            'level_up': [(600, 100), (800, 100), (1000, 100), (1200, 300)],
            'task_complete': [(1000, 80), (1200, 80), (1000, 120)],
            'combo': [(600, 100), (800, 100), (1200, 300)],
            'achievement': [(800, 100), (1000, 100), (800, 100), (1200, 400)],
            'pomodoro_start': [(600, 150), (800, 150)],
            'pomodoro_end': [(1200, 150), (1000, 150), (800, 150)],
            'potion_use': [(500, 100), (700, 150)],
            'powerup': [(400, 100), (600, 100), (800, 200)]
        }
        
        # Carregar sons iniciais
        self.reload_sounds()
    
    def _find_sound_file(self, name: str) -> Optional[Path]:
        """Procura arquivo de som com extensões suportadas."""
        if not self.sound_path.exists():
            return None
        
        # Extensões suportadas dependem do backend
        extensions = ['.wav', '.ogg', '.mp3'] if self._pygame_available else ['.wav']
        
        for ext in extensions:
            filepath = self.sound_path / f"{name}{ext}"
            if filepath.exists():
                return filepath
        
        return None
    
    def reload_sounds(self):
        """Recarrega arquivos de som do disco."""
        if self._pygame_available:
            import pygame
        
        # Lista de efeitos conhecidos
        known_effects = [
            'mana_gain', 'mana_loss', 'level_up', 'task_complete', 'combo', 
            'achievement', 'pomodoro_start', 'pomodoro_end', 'potion_use', 'powerup'
        ]
        
        loaded_count = 0
        
        for name in known_effects:
            filepath = self._find_sound_file(name)
            if filepath:
                try:
                    if self._pygame_available:
                        # Carregar no objeto Sound do Pygame
                        sound = pygame.mixer.Sound(str(filepath))
                        sound.set_volume(self._volume)
                        self._sounds[name] = sound
                        loaded_count += 1
                    else:
                        # Apenas guardar o caminho para Winsound
                        self._sounds[name] = filepath
                        loaded_count += 1
                except Exception as e:
                    print(f"[SoundManager] Erro arquivo {name}: {e}")
            else:
                # Remove se existia antes (ex: arquivo deletado)
                if name in self._sounds:
                    del self._sounds[name]

        print(f"🔊 Sons carregados: {loaded_count}/{len(known_effects)}")

    def set_volume(self, volume: float):
        """Define o volume global (0.0 a 1.0) - Apenas Pygame."""
        if not self._enabled:
            return
            
        self._volume = max(0.0, min(1.0, volume))
        
        if self._pygame_available:
            # Atualizar volume de sons já carregados
            for sound in self._sounds.values():
                if hasattr(sound, 'set_volume'): # Garantir que é obj Pygame
                    sound.set_volume(self._volume)
                    
            # Tentar tocar um feedback beep se volume > 0 ? (Opcional)
    
    def play_sfx(self, sound_name: str):
        """Toca um efeito sonoro."""
        if not self._enabled:
            return
            
        # 1. Tentar tocar do arquivo carregado
        if sound_name in self._sounds:
            sound_obj = self._sounds[sound_name]
            
            if self._pygame_available:
                # Pygame: fire and forget
                try:
                    sound_obj.play()
                except Exception as e:
                    print(f"Erro Pygame play: {e}")
            else:
                # Winsound: path
                self._play_wav_file(sound_obj)
            return

        # 2. Fallback para beep procedural
        if sound_name in self._fallback_beeps:
            self._play_beep_sequence(self._fallback_beeps[sound_name])
        else:
            if self._volume > 0: # Só loga se não estiver mudo virtualmente
                print(f"⚠️ Som '{sound_name}' não encontrado!")
    
    def _play_wav_file(self, filepath: Path):
        """Toca WAV via winsound (Legacy/Fallback)"""
        def _play():
            try:
                winsound.PlaySound(str(filepath), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()
    
    def _play_beep_sequence(self, sequence: list):
        """Toca beeps via winsound (Fallback)"""
        def _beep():
            try:
                for freq, duration in sequence:
                    winsound.Beep(freq, duration)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def toggle(self):
        self._enabled = not self._enabled
        return self._enabled
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    @property
    def using_pygame(self) -> bool:
        return self._pygame_available


# Instância global
_audio_manager: Optional[SoundManager] = None


def get_audio_manager() -> SoundManager:
    """Retorna a instância global do SoundManager."""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = SoundManager(enabled=True)
    return _audio_manager


# Teste
if __name__ == "__main__":
    import time
    
    print("🎵 Testando SoundManager Híbrido...\n")
    
    audio = SoundManager()
    
    sounds_to_test = [
        'mana_gain',
        'level_up',
        'task_complete',
        'achievement',
    ]
    
    for sound in sounds_to_test:
        print(f"\n▶️ Tocando: {sound}")
        audio.play_sfx(sound)
        time.sleep(1.5)
    
    print("\n✅ Teste concluído!")
