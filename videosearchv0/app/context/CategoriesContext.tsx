'use client';

import React, {
	createContext,
	useContext,
	useState,
	useEffect,
	ReactNode,
} from 'react';
import axios from 'axios';

type Category = {
	key: string;
	doc_count: number;
};

type CategoriesContextType = {
	categories: Category[];
	reloadCategories: () => Promise<void>;
};

const CategoriesContext = createContext<CategoriesContextType | undefined>(
	undefined
);

export const CategoriesProvider = ({ children }: { children: ReactNode }) => {
	const [categories, setCategories] = useState<Category[]>([]);

	const fetchCategories = async () => {
		try {
			const res = await axios.get(
				'http://localhost:5000/api/videos/categories',
				{ headers: { 'x-api-key': 'key1' } }
			);
			setCategories(res.data.data.buckets || []);
		} catch (err) {
			console.error('Failed to fetch categories:', err);
		}
	};

	useEffect(() => {
		fetchCategories();
	}, []);

	return (
		<CategoriesContext.Provider
			value={{ categories, reloadCategories: fetchCategories }}
		>
			{children}
		</CategoriesContext.Provider>
	);
};

export const useCategories = () => {
	const context = useContext(CategoriesContext);
	if (!context)
		throw new Error('useCategories must be used within a CategoriesProvider');
	return context;
};
