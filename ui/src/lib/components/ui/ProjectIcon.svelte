<script lang="ts">
	import {
		FolderKanban, Code, Briefcase, Rocket, BookOpen, Palette,
		Music, Camera, Heart, Star, Zap, Globe, ShoppingCart, Wrench,
		Lightbulb, Target, Trophy, Flame, Leaf, Coffee, Gamepad2,
		GraduationCap, Megaphone, PenTool, Shield, Smartphone, Box, Layers
	} from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	interface Props {
		name: string;
		size?: number;
		class?: string;
	}

	let { name, size = 20, class: className = '' }: Props = $props();

	const iconMap: Record<string, ComponentType> = {
		'folder-kanban': FolderKanban,
		'code': Code,
		'briefcase': Briefcase,
		'rocket': Rocket,
		'book-open': BookOpen,
		'palette': Palette,
		'music': Music,
		'camera': Camera,
		'heart': Heart,
		'star': Star,
		'zap': Zap,
		'globe': Globe,
		'shopping-cart': ShoppingCart,
		'wrench': Wrench,
		'lightbulb': Lightbulb,
		'target': Target,
		'trophy': Trophy,
		'flame': Flame,
		'leaf': Leaf,
		'coffee': Coffee,
		'gamepad-2': Gamepad2,
		'graduation-cap': GraduationCap,
		'megaphone': Megaphone,
		'pen-tool': PenTool,
		'shield': Shield,
		'smartphone': Smartphone,
		'box': Box,
		'layers': Layers,
	};

	let IconComponent = $derived(iconMap[name] ?? FolderKanban);
</script>

<IconComponent {size} class={className} />
